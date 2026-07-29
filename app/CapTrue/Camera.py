import os
import threading
import time
from contextlib import contextmanager
from threading import Thread
import queue
import socket
import struct
from ctypes import POINTER, byref, c_ubyte, cast, create_string_buffer, sizeof
from pathlib import Path

import numpy as np
import yaml

import CONFIG
from BKVisionCamera.areascancamera.hikvision.MvImport.CameraParams_const import (
    MV_ACCESS_Exclusive,
    MV_CAMERALINK_DEVICE,
    MV_GIGE_DEVICE,
    MV_USB_DEVICE,
)
from BKVisionCamera.areascancamera.hikvision.MvImport.CameraParams_header import (
    MV_CC_DEVICE_INFO,
    MV_CC_DEVICE_INFO_LIST,
    MV_FRAME_OUT_INFO_EX,
    MVCC_FLOATVALUE,
    MVCC_INTVALUE,
)
from BKVisionCamera.areascancamera.hikvision.MvImport.MvCameraControl_class import MvCamera
from BKVisionCamera.areascancamera.hikvision.MvImport.MvErrorDefine_const import (
    MV_E_GC_TIMEOUT,
    MV_E_NODATA,
    MV_OK,
)
from harvesters.core import Buffer, ImageAcquirer

from Log import logger
from core import get_camera_by_sn


SICK_DEVICE_RESET_AFTER_LOCK_FAILURES = int(
    os.getenv("LG3D_SICK_DEVICE_RESET_AFTER_LOCK_FAILURES", "3"))
CAMERA_TEMPERATURE_REFRESH_SECONDS = float(
    os.getenv("LG3D_CAMERA_TEMPERATURE_REFRESH_SECONDS", "5"))
CAMERA_PARAM_REFRESH_SECONDS = float(
    os.getenv("LG3D_CAMERA_PARAM_REFRESH_SECONDS", "2"))
SICK_FETCH_TIMEOUT_SECONDS = max(
    0.1, float(os.getenv("LG3D_SICK_FETCH_TIMEOUT_SECONDS", "1.0")))
SICK_FETCH_STALL_SECONDS = max(
    SICK_FETCH_TIMEOUT_SECONDS + 2.0,
    float(os.getenv("LG3D_SICK_FETCH_STALL_SECONDS", "10.0")),
)
SICK_CONTROL_STALL_SECONDS = max(
    1.0, float(os.getenv("LG3D_SICK_CONTROL_STALL_SECONDS", "30.0")))
HIK_FRAME_TIMEOUT_MS = max(
    100, int(os.getenv("LG3D_HIK_FRAME_TIMEOUT_MS", "1000")))
HIK_SDK_STALL_SECONDS = max(
    HIK_FRAME_TIMEOUT_MS / 1000.0 + 2.0,
    float(os.getenv("LG3D_HIK_SDK_STALL_SECONDS", "10.0")),
)
HIK_CONNECT_STALL_SECONDS = max(
    1.0, float(os.getenv("LG3D_HIK_CONNECT_STALL_SECONDS", "30.0")))
HIK_CONTROL_LOCK_TIMEOUT_SECONDS = max(
    0.05,
    float(os.getenv("LG3D_HIK_CONTROL_LOCK_TIMEOUT_SECONDS", "1.0")),
)
HIK_CONNECTION_CHECK_SECONDS = max(
    1.0, float(os.getenv("LG3D_HIK_CONNECTION_CHECK_SECONDS", "5.0")))
HIK_RECONNECT_STABLE_SECONDS = max(
    1.0, float(os.getenv("LG3D_HIK_RECONNECT_STABLE_SECONDS", "30.0")))


class NativeCallMonitor:
    """Record native SDK calls without ever making status readers wait on them."""

    def __init__(self):
        self._lock = threading.Lock()
        self._token = None
        self._name = ""
        self._started_at = 0.0
        self._started_monotonic = 0.0
        self._stall_after = 0.0

    @contextmanager
    def track(self, name, stall_after):
        token = object()
        with self._lock:
            self._token = token
            self._name = str(name)
            self._started_at = time.time()
            self._started_monotonic = time.monotonic()
            self._stall_after = max(float(stall_after), 0.0)
        try:
            yield
        finally:
            with self._lock:
                # A future call must not be cleared by an older call's finally
                # block. Calls are normally serialized, but this keeps status
                # truthful even during shutdown races.
                if self._token is token:
                    self._token = None
                    self._name = ""
                    self._started_at = 0.0
                    self._started_monotonic = 0.0
                    self._stall_after = 0.0

    def status(self):
        with self._lock:
            active = self._token is not None
            name = self._name
            started_at = self._started_at
            started_monotonic = self._started_monotonic
            stall_after = self._stall_after
        age = max(time.monotonic() - started_monotonic,
                  0.0) if active else 0.0
        return {
            "active": active,
            "name": name,
            "startedAt": started_at,
            "age": age if active else None,
            "stallAfter": stall_after if active else None,
            "stalled": bool(active and stall_after > 0 and age > stall_after),
        }


class SickCamera:
    def __init__(self, sn):
        super().__init__()
        self.sn = sn
        self._camera_lock = threading.RLock()
        self._sdk_monitor = NativeCallMonitor()
        self._reconnect_event = threading.Event()
        self._device_reset_event = threading.Event()
        self._consecutive_start_failures = 0
        self._device_reset_attempted = False
        self._last_start_diagnostics = {}
        self._last_error = ""
        self._last_action = "initializing"
        self._last_action_time = time.time()
        self._last_connect_time = 0.0
        self._last_disconnect_time = 0.0
        self._last_acquiring = False
        # Keep only the most recently discarded wrapper so repeated cleanup
        # paths cannot stop/destroy the same native handle twice. Replacing
        # this reference on the next connection also keeps the guard bounded.
        self._last_discarded_camera = None
        self._temperature_celsius = None
        self._temperature_source = ""
        self._temperature_error = ""
        self._temperature_time = 0.0
        self._bd_config = {}
        self.camera: ImageAcquirer | None = None
        self._connect()
        self.globCameraInfo = self.get_camera_config()

    def _connect(self) -> ImageAcquirer:
        with self._sdk_monitor.track("connect", SICK_CONTROL_STALL_SECONDS):
            camera = get_camera_by_sn(self.sn)
            if camera is None:
                raise RuntimeError(f"相机初始化失败: {self.sn}")

            self.camera = camera
            try:
                self.setConfig()
            except Exception as e:
                self._last_error = str(e)
                self._discard_camera(camera, "configure failed")
                raise
            try:
                self._bd_config = self._read_bd_config(camera)
            except Exception as e:
                # Some test/simulator devices and older firmware do not expose
                # the 3D coordinate nodes. This metadata must not prevent the
                # camera from reconnecting.
                self._bd_config = {}
                logger.warning(
                    "read sick camera coordinate config failed: sn=%s error=%s",
                    self.sn,
                    e,
                )
            self._refresh_temperature(camera, force=True)
            self._last_error = ""
            self._last_action = "connected"
            self._last_action_time = time.time()
            self._last_connect_time = self._last_action_time
            return camera

    def _get_camera(self) -> ImageAcquirer:
        if self.camera is None:
            return self._connect()
        return self.camera

    @staticmethod
    def _node_value(node_map, name):
        try:
            return getattr(node_map, name).value
        except Exception:
            return None

    @staticmethod
    def _node_access(node_map, name):
        try:
            return str(getattr(node_map, name).get_access_mode())
        except Exception:
            return "unknown"

    def _get_start_diagnostics(self, camera):
        node_map = camera.remote_device.node_map
        return {
            "acquisitionStartAccess":
            self._node_access(node_map, "AcquisitionStart"),
            "acquisitionStopAccess":
            self._node_access(node_map, "AcquisitionStop"),
            "deviceResetAccess":
            self._node_access(node_map, "DeviceReset"),
            "registerStreamingEndAccess":
            self._node_access(node_map, "DeviceRegistersStreamingEnd"),
            "deviceRegistersStreamingActive":
            self._node_value(node_map, "DeviceRegistersStreamingActive"),
            "deviceRegistersValid":
            self._node_value(node_map, "DeviceRegistersValid"),
            "deviceScanType":
            self._node_value(node_map, "DeviceScanType"),
            "acquisitionMode":
            self._node_value(node_map, "AcquisitionMode"),
            "tlParamsLocked":
            self._node_value(node_map, "TLParamsLocked"),
            "deviceCurrentBootPath":
            self._node_value(node_map, "DeviceCurrentBootPath"),
            "deviceFirmwareVersion":
            self._node_value(node_map, "DeviceFirmwareVersion"),
        }

    def _refresh_temperature(self, camera, force=False):
        now = time.time()
        if (not force and self._temperature_time
                and now - self._temperature_time
                < CAMERA_TEMPERATURE_REFRESH_SECONDS):
            return
        if camera is None:
            return

        node_map = camera.remote_device.node_map
        errors = []
        for node_name in ("DeviceTemperature", "Temperature"):
            try:
                value = float(getattr(node_map, node_name).value)
                if not np.isfinite(value):
                    raise ValueError(f"non-finite value: {value}")
                self._temperature_celsius = value
                self._temperature_source = node_name
                self._temperature_error = ""
                self._temperature_time = now
                return
            except Exception as e:
                errors.append(f"{node_name}: {e}")

        self._temperature_error = "; ".join(errors)
        self._temperature_time = now

    @staticmethod
    def _is_acquisition_start_lock(error):
        error_text = str(error)
        return ("AcquisitionStart" in error_text
                and "not writable" in error_text.lower())

    def _end_register_streaming(self, camera):
        try:
            node_map = camera.remote_device.node_map
        except Exception as e:
            logger.debug(
                "read sick camera register streaming state failed: sn=%s error=%s",
                self.sn,
                e,
            )
            return False
        if self._node_value(
                node_map, "DeviceRegistersStreamingActive") is not True:
            return False
        try:
            node_map.DeviceRegistersStreamingEnd.execute()
            logger.warning(
                "ended stale sick camera register streaming session: sn=%s",
                self.sn,
            )
            return True
        except Exception as e:
            logger.warning(
                "end sick camera register streaming session failed: sn=%s error=%s",
                self.sn,
                e,
            )
            return False

    def _should_reset_device(self, error):
        return (SICK_DEVICE_RESET_AFTER_LOCK_FAILURES > 0
                and self._is_acquisition_start_lock(error)
                and not self._device_reset_attempted
                and self._consecutive_start_failures >=
                SICK_DEVICE_RESET_AFTER_LOCK_FAILURES)

    def _discard_camera(self, camera, reason, reset_device=False):
        if camera is None or camera is self._last_discarded_camera:
            return False
        self._last_discarded_camera = camera
        if self.camera is camera:
            self.camera = None
        self._last_action = "resetting" if reset_device else "disconnected"
        self._last_action_time = time.time()
        self._last_disconnect_time = self._last_action_time
        self._last_acquiring = False

        with self._sdk_monitor.track("cleanup_stop",
                                     SICK_CONTROL_STALL_SECONDS):
            try:
                camera.stop()
            except Exception as e:
                logger.warning(
                    "sick camera rollback stop failed: sn=%s reason=%s error=%s",
                    self.sn,
                    reason,
                    e,
                )

        with self._sdk_monitor.track("cleanup_register_streaming",
                                     SICK_CONTROL_STALL_SECONDS):
            self._end_register_streaming(camera)

        if reset_device:
            # Mark before executing because a successful reset immediately
            # drops the control connection and may itself raise in the client.
            self._device_reset_attempted = True
            with self._sdk_monitor.track("cleanup_device_reset",
                                         SICK_CONTROL_STALL_SECONDS):
                try:
                    camera.remote_device.node_map.DeviceReset.execute()
                    logger.warning(
                        "soft reset sick camera: sn=%s reason=%s failures=%s",
                        self.sn,
                        reason,
                        self._consecutive_start_failures,
                    )
                except Exception as e:
                    logger.error(
                        "soft reset sick camera failed: sn=%s reason=%s failures=%s error=%s",
                        self.sn,
                        reason,
                        self._consecutive_start_failures,
                        e,
                    )

        with self._sdk_monitor.track("cleanup_destroy",
                                     SICK_CONTROL_STALL_SECONDS):
            try:
                camera.destroy()
            except Exception as e:
                logger.warning(
                    "sick camera rollback destroy failed: sn=%s reason=%s error=%s",
                    self.sn,
                    reason,
                    e,
                )
        return True

    def get_camera_config(self):
        re_dict = {}
        skipped_count = 0
        camera = self._get_camera()
        with self._sdk_monitor.track("read_config",
                                     SICK_CONTROL_STALL_SECONDS * 2):
            for itemName in dir(camera.remote_device.node_map):
                try:
                    item = getattr(camera.remote_device.node_map, itemName)
                    re_dict[itemName] = item.value
                except Exception:
                    skipped_count += 1
        logger.debug(
            "loaded sick camera config: sn=%s item_count=%s skipped_count=%s",
            self.sn,
            len(re_dict),
            skipped_count,
        )

        return re_dict

    def setConfig(self):
        # self.camera.remote_device.node_map
        # self.camera.remote_device.node_map.TriggerMode.value = "On"
        camera = self._get_camera()
        camera.remote_device.node_map.DeviceScanType.value = "Linescan3D"

    @staticmethod
    def _read_bd_config(camera):
        bdData = {}
        for key in ["CoordinateA", "CoordinateB", "CoordinateC"]:
            camera.remote_device.node_map.Scan3dCoordinateSelector.value = key
            bdData[key] = {
                "Scan3dCoordinateOffset": camera.remote_device.node_map.Scan3dCoordinateOffset.value,
                "Scan3dCoordinateScale": camera.remote_device.node_map.Scan3dCoordinateScale.value,
                "Scan3dAxisMax": camera.remote_device.node_map.Scan3dAxisMax.value,
                "Scan3dAxisMin": camera.remote_device.node_map.Scan3dAxisMin.value,
                # "Scan3dInvalidDataValue": self.camera.remote_device.node_map.Scan3dInvalidDataValue.value,
                # "Scan3dRectificationSpread": self.camera.remote_device.node_map.Scan3dRectificationSpread.value,
            }
        return bdData

    def getBDconfig(self):
        # Coordinate calibration is static for one connection. Avoid twelve
        # GenICam node reads on every captured frame.
        return {
            key: dict(value)
            for key, value in self._bd_config.items()
        }

    @staticmethod
    def _is_fetch_timeout(error):
        return type(error).__name__ == "TimeoutException"

    def get_buffer(self) -> Buffer | None:
        self.process_pending_actions()
        camera = self._get_camera()
        with self._sdk_monitor.track("fetch", SICK_FETCH_STALL_SECONDS):
            try:
                return camera.fetch(timeout=SICK_FETCH_TIMEOUT_SECONDS)
            except Exception as e:
                if self._is_fetch_timeout(e):
                    return None
                raise

    def open(self):
        with self._camera_lock:
            camera = self._get_camera()
            start_time = time.time()
            try:
                with self._sdk_monitor.track("start",
                                             SICK_CONTROL_STALL_SECONDS):
                    camera.start()
            except Exception as e:
                # Harvesters marks the acquirer as active and locks/announces
                # buffers before executing AcquisitionStart. If that command
                # fails, __enter__ raises and __exit__ is never called. Fully
                # discard the partial session so the outer capture loop can
                # reconnect instead of retrying the stale command forever.
                self._consecutive_start_failures += 1
                diagnostics = self._get_start_diagnostics(camera)
                self._last_start_diagnostics = diagnostics
                self._last_error = str(e)
                logger.warning(
                    "sick camera start diagnostics: sn=%s failure=%s state=%s",
                    self.sn,
                    self._consecutive_start_failures,
                    diagnostics,
                )
                self._discard_camera(
                    camera,
                    "start failed",
                    reset_device=self._should_reset_device(e),
                )
                raise
            self._consecutive_start_failures = 0
            self._device_reset_attempted = False
            self._last_error = ""
            self._last_action = "acquiring"
            self._last_action_time = time.time()
            self._last_acquiring = True
            elapsed = time.time() - start_time
            logger.info("sick camera started: sn=%s elapsed_s=%.3f", self.sn, elapsed)

    def release(self):
        with self._camera_lock:
            camera = self.camera
            if camera is None:
                return
            # A stopped ImageAcquirer still owns GenTL threads, buffers and OS
            # handles. Destroy it at the end of the acquisition session so a
            # retry or capture-unit replacement cannot retain the old SDK
            # session until garbage collection.
            self._discard_camera(camera, "release")
            self._last_action = "stopped"
            self._last_action_time = time.time()
            self._last_acquiring = False

    def refresh_telemetry(self):
        lock_acquired = self._camera_lock.acquire(blocking=False)
        if not lock_acquired:
            return False
        try:
            camera = self.camera
            if camera is None:
                return False
            with self._sdk_monitor.track("read_temperature",
                                         SICK_FETCH_STALL_SECONDS):
                self._refresh_temperature(camera)
            return True
        finally:
            self._camera_lock.release()

    @staticmethod
    def _is_acquiring(camera) -> bool:
        if camera is None:
            return False
        try:
            acquiring = camera.is_acquiring
            return bool(acquiring() if callable(acquiring) else acquiring)
        except Exception:
            return False

    def get_status(self, refresh_live=False) -> dict:
        lock_acquired = self._camera_lock.acquire(blocking=False)
        try:
            camera = self.camera
            connected = camera is not None
            if lock_acquired and refresh_live:
                acquiring = self._is_acquiring(camera)
                self._last_acquiring = acquiring
            else:
                acquiring = self._last_acquiring
            native_sdk = self._sdk_monitor.status()
            temperature_age = (
                max(time.time() - self._temperature_time, 0)
                if self._temperature_time else None)
            return {
                "ok": connected and not self._last_error
                and not native_sdk["stalled"],
                "connected": connected,
                "acquiring": acquiring,
                "sn": self.sn,
                "lastError": self._last_error,
                "lastAction": self._last_action,
                "lastActionTime": self._last_action_time,
                "lastConnectTime": self._last_connect_time,
                "lastDisconnectTime": self._last_disconnect_time,
                "consecutiveStartFailures":
                self._consecutive_start_failures,
                "deviceResetAttempted":
                self._device_reset_attempted,
                "lastStartDiagnostics":
                dict(self._last_start_diagnostics),
                "temperatureCelsius":
                self._temperature_celsius,
                "temperatureAvailable":
                self._temperature_celsius is not None,
                "temperatureSource":
                self._temperature_source,
                "temperatureTime":
                self._temperature_time,
                "temperatureAge":
                temperature_age,
                "temperatureStale":
                (not connected or temperature_age is None
                 or temperature_age > CAMERA_TEMPERATURE_REFRESH_SECONDS * 3),
                "temperatureError":
                self._temperature_error,
                "nativeSdk":
                native_sdk,
                "requiresProcessRestart":
                native_sdk["stalled"],
            }
        finally:
            if lock_acquired:
                self._camera_lock.release()

    def request_reconnect(self) -> dict:
        # API/control threads only enqueue the action. Calling stop/destroy
        # here used to make the endpoint wait forever behind a blocked fetch.
        self._last_action = "manual reconnect requested"
        self._last_action_time = time.time()
        self._last_error = ""
        self._device_reset_attempted = False
        self._reconnect_event.set()
        return {
            "ok": True,
            "action": "reconnect3D",
            "message": "3D camera reconnect requested",
            "queued": True,
            "camera": self.get_status(),
        }

    def request_device_reset(self) -> dict:
        self._last_action = "manual device reset requested"
        self._last_action_time = time.time()
        self._last_error = ""
        self._device_reset_event.set()
        return {
            "ok": True,
            "action": "reset3D",
            "message": "3D camera device reset requested",
            "queued": True,
            "camera": self.get_status(),
        }

    def process_pending_actions(self):
        reset_requested = self._device_reset_event.is_set()
        reconnect_requested = self._reconnect_event.is_set()
        if not reset_requested and not reconnect_requested:
            return False

        with self._camera_lock:
            camera = self.camera
            if reset_requested and camera is None:
                camera = self._connect()
            action = "manual device reset" if reset_requested else "manual reconnect"
            self._last_action = action
            self._last_action_time = time.time()
            self._last_error = ""
            if camera is not None:
                with self._sdk_monitor.track(
                        "reset" if reset_requested else "reconnect_cleanup",
                        SICK_CONTROL_STALL_SECONDS):
                    self._discard_camera(
                        camera,
                        action,
                        reset_device=reset_requested,
                    )
            self._device_reset_event.clear()
            self._reconnect_event.clear()
            self._last_action = f"{action} completed"
            self._last_action_time = time.time()
        raise RuntimeError(f"3D camera {action} requested")

    def __enter__(self):
        # 初始化或打开相机等操作
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # 清理资源，例如关闭相机
        self.release()

    def get_last_frame(self):
        return None

    def if_save_index(self):
        return False

class DaHengCamera(Thread): # Process
    EXTERNAL_TRIGGER_NO_FRAME_CODES = {MV_E_NODATA, MV_E_GC_TIMEOUT}

    def __init__(self, yaml_config, camera_key=None, max_queue_size=2):
        super().__init__()
        self.yaml_config = yaml_config
        self.camera_key = camera_key or Path(str(yaml_config)).stem
        self.yaml_path = CONFIG.CONFIG_DIR / self.yaml_config if self.yaml_config else None
        self.config = self._load_yaml_config()
        self.camera_param_file = self._get_camera_param_file()
        self.capter = None
        self.connected = False
        self.state = "init"
        self.last_error = ""
        self.last_frame = None
        self.last_frame_time = 0
        self.last_connect_time = 0
        self.last_disconnect_time = 0
        self.last_reconnect_request_time = 0
        self.connect_attempts = 0
        self.frame_id = 0
        self.empty_frame_count = 0
        self.frame_error_count = 0
        self.dropped_frames = 0
        self.running = True
        self.width = 0
        self.height = 0
        self.payload_size = 0
        self._frame_buffer = None
        self._frame_buffer_size = 0
        self.temperature_celsius = None
        self.temperature_source = ""
        self.temperature_error = ""
        self.temperature_time = 0.0
        self.exposure_time = None
        self.gain = None
        self.param_errors = {}
        self.param_time = 0.0
        self.max_queue_size = max_queue_size
        self.frame_queue = queue.Queue(maxsize=max_queue_size)
        self._reconnect_event = threading.Event()
        self._sdk_lock = threading.RLock()
        self._state_lock = threading.RLock()
        self._sdk_monitor = NativeCallMonitor()
        self.daemon = True
        if yaml_config:
            self.start()

    @staticmethod
    def _to_str(data, count=32):
        buffer = create_string_buffer(count)
        buffer.raw = bytes(data[:count])
        return buffer.value.decode("utf-8", errors="ignore")

    @staticmethod
    def _nto(addr):
        return socket.inet_ntoa(struct.pack(">L", addr))

    @staticmethod
    def _format_mac(mac):
        if mac is None:
            return ""
        chars = "".join(ch for ch in str(mac).upper() if ch in "0123456789ABCDEF")
        return ":".join(chars[i:i + 2] for i in range(0, len(chars), 2))

    @classmethod
    def _device_snapshot(cls, dev_info):
        gige_info = dev_info.SpecialInfo.stGigEInfo
        mac_high = dev_info.nMacAddrHigh
        mac_low = dev_info.nMacAddrLow
        mac_address = f"{mac_high:08X}{mac_low:08X}"
        return {
            "ip": cls._nto(gige_info.nCurrentIp),
            "macAddress": cls._format_mac(mac_address),
            "serialNumber": cls._to_str(gige_info.chSerialNumber),
            "modelName": cls._to_str(gige_info.chModelName),
            "userDefinedName": cls._to_str(gige_info.chUserDefinedName),
        }

    def _load_yaml_config(self):
        if self.yaml_path is None:
            return {}
        try:
            with open(self.yaml_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.warning("2D camera %s config load failed: %s, error=%s", self.camera_key, self.yaml_path, e)
            return {}

    def _set_state(self, state, error=None, connected=None):
        with self._state_lock:
            self.state = state
            if error is not None:
                self.last_error = str(error)
            if connected is not None:
                self.connected = connected

    def _enum_devices(self):
        cam = MvCamera()
        dev_list = MV_CC_DEVICE_INFO_LIST()
        ret = cam.MV_CC_EnumDevices(MV_GIGE_DEVICE | MV_USB_DEVICE | MV_CAMERALINK_DEVICE, dev_list)
        if ret != MV_OK:
            raise RuntimeError(f"MV_CC_EnumDevices failed ret=0x{ret:08X}")
        return dev_list

    def _select_device(self, dev_list):
        device_count = int(dev_list.nDeviceNum)
        if device_count <= 0:
            raise RuntimeError("no Hikvision 2D camera found")

        select_type = str(self.config.get("selectType", "index")).lower()
        target_ip = str(self.config.get("ip", "") or "")
        target_mac = self._format_mac(self.config.get("macAddress") or self.config.get("mac"))
        target_sn = str(self.config.get("serialNumber") or self.config.get("sn") or "")
        target_index = int(self.config.get("index", 0) or 0)

        devices = []
        for index in range(device_count):
            dev_info = cast(dev_list.pDeviceInfo[index], POINTER(MV_CC_DEVICE_INFO)).contents
            snapshot = self._device_snapshot(dev_info)
            devices.append((index, dev_info, snapshot))

        for index, dev_info, snapshot in devices:
            if select_type == "ip" and target_ip and snapshot["ip"] == target_ip:
                return dev_info, snapshot
            if select_type in ("mac", "macaddress") and target_mac and snapshot["macAddress"] == target_mac:
                return dev_info, snapshot
            if select_type in ("serial", "serialnumber", "sn") and target_sn and snapshot["serialNumber"] == target_sn:
                return dev_info, snapshot
            if select_type == "index" and index == target_index:
                return dev_info, snapshot

        available = ", ".join(
            f"{idx}:ip={item['ip']},mac={item['macAddress']},sn={item['serialNumber']}"
            for idx, _, item in devices
        )
        raise RuntimeError(
            f"camera {self.camera_key} not found by {select_type}; "
            f"target ip={target_ip}, mac={target_mac}, sn={target_sn}, index={target_index}; "
            f"available [{available}]"
        )

    def _create_camera(self):
        dev_list = self._enum_devices()
        dev_info, snapshot = self._select_device(dev_list)
        cam = MvCamera()
        ret = cam.MV_CC_CreateHandle(dev_info)
        if ret != MV_OK:
            raise RuntimeError(f"MV_CC_CreateHandle failed ret=0x{ret:08X}, device={snapshot}")
        try:
            ret = cam.MV_CC_OpenDevice(MV_ACCESS_Exclusive, 0)
            if ret != MV_OK:
                raise RuntimeError(f"MV_CC_OpenDevice failed ret=0x{ret:08X}, device={snapshot}")
            self._apply_or_save_camera_params(cam)
            self._read_image_shape(cam)
            self._store_camera_params(
                *self._read_camera_params_from_camera(cam))
            self._store_temperature(
                *self._read_temperature_from_camera(cam))
            ret = cam.MV_CC_StartGrabbing()
            if ret != MV_OK:
                raise RuntimeError(f"MV_CC_StartGrabbing failed ret=0x{ret:08X}, device={snapshot}")
            logger.info("2D camera %s opened: %s", self.camera_key, snapshot)
            return cam
        except Exception:
            self._safe_release_camera(cam)
            raise

    def _read_int(self, cam, key):
        value = MVCC_INTVALUE()
        ret = cam.MV_CC_GetIntValue(key, value)
        if ret != MV_OK:
            raise RuntimeError(f"MV_CC_GetIntValue({key}) failed ret=0x{ret:08X}")
        return int(value.nCurValue)

    @staticmethod
    def _read_numeric_param(cam, key):
        errors = []
        value = MVCC_FLOATVALUE()
        try:
            ret = cam.MV_CC_GetFloatValue(key, value)
            if ret == MV_OK:
                result = float(value.fCurValue)
                if np.isfinite(result):
                    return result
                errors.append(f"non-finite float={result}")
            else:
                errors.append(f"float ret=0x{ret:08X}")
        except Exception as e:
            errors.append(f"float: {e}")

        value = MVCC_INTVALUE()
        try:
            ret = cam.MV_CC_GetIntValue(key, value)
            if ret == MV_OK:
                return int(value.nCurValue)
            errors.append(f"int ret=0x{ret:08X}")
        except Exception as e:
            errors.append(f"int: {e}")
        raise RuntimeError("; ".join(errors))

    @classmethod
    def _read_camera_params_from_camera(cls, cam):
        params = {}
        errors = {}
        for public_key, sdk_key in (
                ("exposureTime", "ExposureTime"),
                ("gain", "Gain"),
        ):
            try:
                params[public_key] = cls._read_numeric_param(cam, sdk_key)
            except Exception as e:
                errors[public_key] = str(e)
        return params, errors

    @staticmethod
    def _normalize_param_value(value):
        if value is None:
            return None
        number = float(value)
        if number.is_integer():
            return int(number)
        return number

    def _store_camera_params(self, params, errors):
        if "exposureTime" in params:
            self.exposure_time = self._normalize_param_value(
                params["exposureTime"])
        if "gain" in params:
            self.gain = self._normalize_param_value(params["gain"])
        self.param_errors = dict(errors)
        self.param_time = time.time()

    def _cached_camera_params(self):
        params = {}
        if self.exposure_time is not None:
            params["exposureTime"] = self.exposure_time
        if self.gain is not None:
            params["gain"] = self.gain
        return params

    def _refresh_camera_params(self, force=False):
        now = time.time()
        if (not force and self.param_time
                and now - self.param_time < CAMERA_PARAM_REFRESH_SECONDS):
            return

        lock_acquired = self._sdk_lock.acquire(blocking=False)
        if not lock_acquired:
            return
        try:
            cam = self.capter
            if cam is None:
                return
            with self._sdk_monitor.track("read_params",
                                         HIK_SDK_STALL_SECONDS):
                self._store_camera_params(
                    *self._read_camera_params_from_camera(cam))
        finally:
            self._sdk_lock.release()

    def get_params(self, refresh_live=False):
        if refresh_live:
            self._refresh_camera_params()
        with self._state_lock:
            return dict(self._cached_camera_params())

    @staticmethod
    def _read_temperature_from_camera(cam):
        errors = []

        def read_float(key):
            value = MVCC_FLOATVALUE()
            try:
                ret = cam.MV_CC_GetFloatValue(key, value)
            except Exception as e:
                return None, f"{key}: {e}"
            if ret != MV_OK:
                return None, f"{key}: ret=0x{ret:08X}"
            temperature = float(value.fCurValue)
            if not np.isfinite(temperature):
                return None, f"{key}: non-finite value={temperature}"
            return temperature, ""

        temperature, error = read_float("DeviceTemperature")
        if temperature is not None:
            return temperature, "DeviceTemperature", ""
        errors.append(error)

        # Some Hikrobot models require selecting the sensor component before
        # DeviceTemperature becomes readable.
        set_selector = getattr(cam, "MV_CC_SetEnumValueByString", None)
        if callable(set_selector):
            try:
                selector_ret = set_selector(
                    "DeviceTemperatureSelector", "Sensor")
                if selector_ret == MV_OK:
                    temperature, error = read_float("DeviceTemperature")
                    if temperature is not None:
                        return (
                            temperature,
                            "DeviceTemperature[Sensor]",
                            "",
                        )
                    errors.append(error)
                else:
                    errors.append(
                        "DeviceTemperatureSelector: "
                        f"ret=0x{selector_ret:08X}")
            except Exception as e:
                errors.append(f"DeviceTemperatureSelector: {e}")

        temperature, error = read_float("Temperature")
        if temperature is not None:
            return temperature, "Temperature", ""
        errors.append(error)
        return None, "", "; ".join(errors)

    def _store_temperature(self, temperature, source, error):
        self.temperature_error = error
        self.temperature_time = time.time()
        if temperature is not None:
            self.temperature_celsius = temperature
            self.temperature_source = source

    def _refresh_temperature(self, force=False):
        now = time.time()
        if (not force and self.temperature_time
                and now - self.temperature_time
                < CAMERA_TEMPERATURE_REFRESH_SECONDS):
            return

        lock_acquired = self._sdk_lock.acquire(blocking=False)
        if not lock_acquired:
            return
        try:
            cam = self.capter
            if cam is None:
                return
            with self._sdk_monitor.track("read_temperature",
                                         HIK_SDK_STALL_SECONDS):
                self._store_temperature(
                    *self._read_temperature_from_camera(cam))
        finally:
            self._sdk_lock.release()

    def _set_int(self, cam, key, value):
        ret = cam.MV_CC_SetIntValue(key, int(value))
        if ret != MV_OK:
            raise RuntimeError(f"MV_CC_SetIntValue({key}) failed ret=0x{ret:08X}")

    def _set_numeric_param(self, cam, key, value):
        errors = []
        try:
            ret = cam.MV_CC_SetFloatValue(key, float(value))
            if ret == MV_OK:
                return
            errors.append(f"float ret=0x{ret:08X}")
        except Exception as e:
            errors.append(f"float: {e}")
        try:
            self._set_int(cam, key, value)
            return
        except Exception as e:
            errors.append(f"int: {e}")
        raise RuntimeError("; ".join(errors))

    def _read_image_shape(self, cam):
        self.width = self._read_int(cam, "Width")
        self.height = self._read_int(cam, "Height")
        payload_size = self._read_int(cam, "PayloadSize")
        if payload_size != self.payload_size:
            self._frame_buffer = None
            self._frame_buffer_size = 0
        self.payload_size = payload_size

    def _get_camera_param_file(self):
        if not self.yaml_config:
            return None
        return CONFIG.CONFIG_DIR / "camera_params" / f"{Path(self.yaml_config).stem}.ini"

    def _apply_or_save_camera_params(self, cam):
        if self.camera_param_file is None:
            return

        if self.camera_param_file.exists():
            self._load_camera_params(cam)
            return

        self._apply_yaml_camera_params(cam)
        self._save_camera_params(cam)

    def _apply_yaml_camera_params(self, cam):
        camera_config = self.config.get("cameraConfig", {}) or {}
        for key, sdk_key in (("exposureTime", "ExposureTime"), ("gain", "Gain")):
            value = camera_config.get(key)
            if value is None:
                continue
            try:
                self._set_numeric_param(cam, sdk_key, value)
            except Exception as e:
                logger.warning("2D camera %s set %s=%s failed: %s", self.camera_key, sdk_key, value, e)

    def _load_camera_params(self, cam):
        try:
            ret = cam.MV_CC_FeatureLoad(str(self.camera_param_file))
            if ret != 0:
                logger.warning("2D camera params load failed: %s, ret=%s", self.camera_param_file, ret)
                return
            logger.info("2D camera params loaded: %s", self.camera_param_file)
        except Exception as e:
            logger.warning("2D camera params load failed: %s, error=%s", self.camera_param_file, e)

    def _save_camera_params(self, cam=None):
        try:
            if cam is None:
                cam = self.capter
            if cam is None:
                raise RuntimeError("camera is not connected")
            self.camera_param_file.parent.mkdir(parents=True, exist_ok=True)
            ret = cam.MV_CC_FeatureSave(str(self.camera_param_file))
            if ret != 0:
                logger.warning("2D camera params save failed: %s, ret=%s", self.camera_param_file, ret)
                return
            logger.info("2D camera params saved: %s", self.camera_param_file)
        except Exception as e:
            logger.warning("2D camera params save failed: %s, error=%s", self.camera_param_file, e)

    def _clear_queue(self):
        try:
            while True:
                self.frame_queue.get_nowait()
        except queue.Empty:
            pass

    def _put_latest_frame(self, frame, frame_time):
        item = [frame, frame_time]
        try:
            self.frame_queue.put_nowait(item)
            return
        except queue.Full:
            pass

        try:
            self.frame_queue.get_nowait()
            self.dropped_frames += 1
        except queue.Empty:
            pass

        try:
            self.frame_queue.put_nowait(item)
        except queue.Full:
            self.dropped_frames += 1

    def _safe_release_camera(self, cam):
        if cam is None:
            return
        for action_name, action in (
            ("StopGrabbing", cam.MV_CC_StopGrabbing),
            ("CloseDevice", cam.MV_CC_CloseDevice),
            ("DestroyHandle", cam.MV_CC_DestroyHandle),
        ):
            try:
                ret = action()
                if ret not in (MV_OK,):
                    logger.debug("2D camera %s %s ret=0x%08X", self.camera_key, action_name, ret)
            except Exception as e:
                logger.debug("2D camera %s %s ignored: %s", self.camera_key, action_name, e)

    def _trim_queue(self, max_size):
        try:
            while self.frame_queue.qsize() > max_size:
                self.frame_queue.get_nowait()
        except NotImplementedError:
            try:
                self.frame_queue.get_nowait()
            except queue.Empty:
                pass
        except queue.Empty:
            pass

    def get_last_frame(self, timeout=None):
        if timeout is None:
            return self.frame_queue.get()
        try:
            return self.frame_queue.get(timeout=timeout)
        except queue.Empty:
            raise TimeoutError("2D camera frame timeout")

    def request_reconnect(self):
        self.last_reconnect_request_time = time.time()
        self._set_state("reconnect_requested", connected=self.connected)
        self._reconnect_event.set()

    def stop(self):
        # The acquisition thread owns and releases the SDK handle. Shutdown
        # must never wait for _sdk_lock because a vendor DLL call can retain it
        # indefinitely after a cable pull.
        self.running = False
        self._reconnect_event.set()
        self._set_state("stopping", connected=self.connected)

    def set_params(self, exposure_time=None, gain=None, save=True):
        if not self._sdk_lock.acquire(
                timeout=HIK_CONTROL_LOCK_TIMEOUT_SECONDS):
            raise RuntimeError(
                "2D camera SDK is busy; parameter update timed out")
        try:
            if self.capter is None:
                raise RuntimeError("2D camera is not connected")
            with self._sdk_monitor.track("set_params",
                                         HIK_CONNECT_STALL_SECONDS):
                if exposure_time is not None:
                    self._set_numeric_param(
                        self.capter, "ExposureTime", exposure_time)
                if gain is not None:
                    self._set_numeric_param(self.capter, "Gain", gain)
                if save:
                    self._save_camera_params(self.capter)
                self._store_camera_params(
                    *self._read_camera_params_from_camera(self.capter))
        finally:
            self._sdk_lock.release()

    def _get_frame_once(self, cam, timeout_ms=1000):
        if self.payload_size <= 0:
            self._read_image_shape(cam)
        st_out_frame = MV_FRAME_OUT_INFO_EX()
        if (self._frame_buffer is None
                or self._frame_buffer_size != int(self.payload_size)):
            self._frame_buffer = (c_ubyte * int(self.payload_size))()
            self._frame_buffer_size = int(self.payload_size)
        p_data = self._frame_buffer
        ret = cam.MV_CC_GetOneFrameTimeout(byref(p_data), sizeof(p_data), st_out_frame, int(timeout_ms))
        if ret in self.EXTERNAL_TRIGGER_NO_FRAME_CODES:
            return None, ret
        if ret != MV_OK:
            raise RuntimeError(f"MV_CC_GetOneFrameTimeout failed ret=0x{ret:08X}")
        frame_len = int(st_out_frame.nWidth * st_out_frame.nHeight)
        frame = np.frombuffer(p_data, count=frame_len, dtype=np.uint8).reshape(
            (int(st_out_frame.nHeight), int(st_out_frame.nWidth))
        ).copy()
        return frame, ret

    @staticmethod
    def _is_device_connected(cam):
        is_connected = getattr(cam, "MV_CC_IsDeviceConnected", None)
        if not callable(is_connected):
            return True
        return bool(is_connected())

    def get_status(self, refresh_live=False):
        if refresh_live:
            self._refresh_temperature()
            self._refresh_camera_params()
        native_sdk = self._sdk_monitor.status()
        with self._state_lock:
            last_frame_time = self.last_frame_time
            temperature_age = (
                max(time.time() - self.temperature_time, 0)
                if self.temperature_time else None)
            param_age = (
                max(time.time() - self.param_time, 0)
                if self.param_time else None)
            return {
                "ok": self.connected and not native_sdk["stalled"],
                "state": self.state,
                "connected": self.connected,
                "lastError": self.last_error,
                "lastFrameTime": last_frame_time,
                "lastFrameAge": max(time.time() - last_frame_time, 0) if last_frame_time else None,
                "lastConnectTime": self.last_connect_time,
                "lastDisconnectTime": self.last_disconnect_time,
                "lastReconnectRequestTime": self.last_reconnect_request_time,
                "connectAttempts": self.connect_attempts,
                "frameId": self.frame_id,
                "emptyFrameCount": self.empty_frame_count,
                "frameErrorCount": self.frame_error_count,
                "droppedFrames": self.dropped_frames,
                "width": self.width,
                "height": self.height,
                "params": dict(self._cached_camera_params()),
                "source": "camera" if self.param_time else "config",
                "paramTime": self.param_time,
                "paramAge": param_age,
                "paramErrors": dict(self.param_errors),
                "temperatureCelsius": self.temperature_celsius,
                "temperatureAvailable":
                self.temperature_celsius is not None,
                "temperatureSource": self.temperature_source,
                "temperatureTime": self.temperature_time,
                "temperatureAge": temperature_age,
                "temperatureStale":
                (not self.connected or temperature_age is None
                 or temperature_age > CAMERA_TEMPERATURE_REFRESH_SECONDS * 3),
                "temperatureError": self.temperature_error,
                "nativeSdk": native_sdk,
                "requiresProcessRestart": native_sdk["stalled"],
            }

    def run(self):
        if not self.yaml_config:
            self._set_state("disabled", "2D camera yaml_config missing", connected=False)
            logger.error("2D camera yaml_config missing, capture thread not started")
            return

        reconnect_delay = 1

        while self.running:
            cam = None
            failure = None
            try:
                self._reconnect_event.clear()
                self.connect_attempts += 1
                self._set_state("connecting", "", connected=False)
                with self._sdk_monitor.track("connect",
                                             HIK_CONNECT_STALL_SECONDS):
                    cam = self._create_camera()
                if not self.running:
                    break
                with self._sdk_lock:
                    self.capter = cam
                self.last_connect_time = time.time()
                self._set_state("streaming", "", connected=True)
                self._clear_queue()
                connected_monotonic = time.monotonic()
                last_wait_log = 0.0
                next_connection_check = time.monotonic()

                while self.running:
                    if self._reconnect_event.is_set():
                        raise RuntimeError("Manual reconnect requested")

                    now_monotonic = time.monotonic()
                    if (now_monotonic - connected_monotonic
                            >= HIK_RECONNECT_STABLE_SECONDS):
                        reconnect_delay = 1
                    with self._sdk_lock:
                        if now_monotonic >= next_connection_check:
                            with self._sdk_monitor.track(
                                    "connection_check",
                                    HIK_SDK_STALL_SECONDS):
                                if not self._is_device_connected(cam):
                                    raise RuntimeError(
                                        "2D camera device connection lost")
                            next_connection_check = (
                                now_monotonic + HIK_CONNECTION_CHECK_SECONDS)
                        with self._sdk_monitor.track(
                                 "fetch", HIK_SDK_STALL_SECONDS):
                            # The SDK call can wait for an external trigger;
                            # release the previous delivered frame before it.
                            frame = None
                            frame, ret = self._get_frame_once(
                                cam, timeout_ms=HIK_FRAME_TIMEOUT_MS)

                    now = time.time()
                    # Refresh telemetry in the camera worker. Status endpoints
                    # only read the cache and never enter vendor DLLs.
                    self._refresh_temperature()
                    self._refresh_camera_params()
                    if frame is None:
                        self.empty_frame_count += 1
                        self._set_state("waiting_trigger", "", connected=True)
                        if now - last_wait_log >= 60:
                            logger.debug(
                                "2D camera %s waiting external trigger (no image, ret=0x%08X, empty=%s)",
                                self.camera_key,
                                ret,
                                self.empty_frame_count,
                            )
                            last_wait_log = now
                        continue
                    self.empty_frame_count = 0
                    self.frame_error_count = 0
                    reconnect_delay = 1
                    self.last_frame_time = now
                    self.frame_id += 1
                    self._set_state("streaming", "", connected=True)
                    self._put_latest_frame(frame, now)
            except Exception as e:
                failure = e
                self.frame_error_count += 1
                self.last_disconnect_time = time.time()
                self._set_state("reconnecting", e, connected=False)
                logger.warning(
                    "2D camera %s disconnected, retrying in %ss: %s",
                    self.camera_key,
                    reconnect_delay,
                    e,
                )
                self._clear_queue()
            finally:
                lock_acquired = self._sdk_lock.acquire(
                    timeout=HIK_CONTROL_LOCK_TIMEOUT_SECONDS)
                if lock_acquired:
                    try:
                        if self.capter is cam:
                            self.capter = None
                    finally:
                        self._sdk_lock.release()
                elif cam is not None:
                    logger.error(
                        "2D camera %s could not detach SDK handle during cleanup",
                        self.camera_key,
                    )
                if cam is not None and lock_acquired:
                    with self._sdk_monitor.track(
                            "release", HIK_CONNECT_STALL_SECONDS):
                        self._safe_release_camera(cam)

            if not self.running:
                self._set_state("stopped", "", connected=False)
                break
            if failure is None:
                continue
            self._reconnect_event.wait(timeout=reconnect_delay)
            reconnect_delay = min(reconnect_delay * 2, 5)
