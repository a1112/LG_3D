import threading
import time
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


class SickCamera:
    def __init__(self, sn):
        super().__init__()
        self.sn = sn
        self.camera = get_camera_by_sn(sn)
        if self.camera is None:
            raise Exception(f"相机 初始化失败: {sn}")
        self.setConfig()
        self.camera:ImageAcquirer
        self.globCameraInfo = self.get_camera_config()


    def get_camera_config(self):
        # print(self.camera.remote_device.node_map.load_xml_from_file)
        re_dict = {}
        for itemName in dir(self.camera.remote_device.node_map):
            try:
                item = getattr(self.camera.remote_device.node_map, itemName)
                re_dict[itemName] = item.value
            except BaseException as e:
                pass
        print(re_dict)

        return re_dict

    def setConfig(self):
        # self.camera.remote_device.node_map
        # self.camera.remote_device.node_map.TriggerMode.value = "On"
        self.camera.remote_device.node_map.DeviceScanType.value = "Linescan3D"

    def getBDconfig(self):
        bdData = {}
        for key in ["CoordinateA", "CoordinateB", "CoordinateC"]:
            self.camera.remote_device.node_map.Scan3dCoordinateSelector.value = key
            bdData[key] = {
                "Scan3dCoordinateOffset": self.camera.remote_device.node_map.Scan3dCoordinateOffset.value,
                "Scan3dCoordinateScale": self.camera.remote_device.node_map.Scan3dCoordinateScale.value,
                "Scan3dAxisMax": self.camera.remote_device.node_map.Scan3dAxisMax.value,
                "Scan3dAxisMin": self.camera.remote_device.node_map.Scan3dAxisMin.value,
                # "Scan3dInvalidDataValue": self.camera.remote_device.node_map.Scan3dInvalidDataValue.value,
                # "Scan3dRectificationSpread": self.camera.remote_device.node_map.Scan3dRectificationSpread.value,
            }
        return bdData

    def get_buffer(self) -> Buffer:
        return self.camera.fetch()

    def open(self):
        sT = time.time()
        self.camera.start()
        eT = time.time()
        print(f"start: {eT-sT} mm")

    def release(self):
        self.camera.stop()

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
        self.width = 0
        self.height = 0
        self.payload_size = 0
        self.max_queue_size = max_queue_size
        self.frame_queue = queue.Queue(maxsize=max_queue_size)
        self._reconnect_event = threading.Event()
        self._sdk_lock = threading.RLock()
        self._state_lock = threading.RLock()
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
            logger.warning(f"2D camera {self.camera_key} config load failed: {self.yaml_path}, error={e}")
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
            ret = cam.MV_CC_StartGrabbing()
            if ret != MV_OK:
                raise RuntimeError(f"MV_CC_StartGrabbing failed ret=0x{ret:08X}, device={snapshot}")
            logger.info(f"2D camera {self.camera_key} opened: {snapshot}")
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

    def _set_int(self, cam, key, value):
        ret = cam.MV_CC_SetIntValue(key, int(value))
        if ret != MV_OK:
            raise RuntimeError(f"MV_CC_SetIntValue({key}) failed ret=0x{ret:08X}")

    def _read_image_shape(self, cam):
        self.width = self._read_int(cam, "Width")
        self.height = self._read_int(cam, "Height")
        self.payload_size = self._read_int(cam, "PayloadSize")

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
                self._set_int(cam, sdk_key, value)
            except Exception as e:
                logger.warning(f"2D camera {self.camera_key} set {sdk_key}={value} failed: {e}")

    def _load_camera_params(self, cam):
        try:
            ret = cam.MV_CC_FeatureLoad(str(self.camera_param_file))
            if ret != 0:
                logger.warning(f"2D camera params load failed: {self.camera_param_file}, ret={ret}")
                return
            logger.info(f"2D camera params loaded: {self.camera_param_file}")
        except Exception as e:
            logger.warning(f"2D camera params load failed: {self.camera_param_file}, error={e}")

    def _save_camera_params(self, cam=None):
        try:
            if cam is None:
                cam = self.capter
            if cam is None:
                raise RuntimeError("camera is not connected")
            self.camera_param_file.parent.mkdir(parents=True, exist_ok=True)
            ret = cam.MV_CC_FeatureSave(str(self.camera_param_file))
            if ret != 0:
                logger.warning(f"2D camera params save failed: {self.camera_param_file}, ret={ret}")
                return
            logger.info(f"2D camera params saved: {self.camera_param_file}")
        except Exception as e:
            logger.warning(f"2D camera params save failed: {self.camera_param_file}, error={e}")

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
                    logger.debug(f"2D camera {self.camera_key} {action_name} ret=0x{ret:08X}")
            except Exception as e:
                logger.debug(f"2D camera {self.camera_key} {action_name} ignored: {e}")

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
        self._reconnect_event.set()

    def set_params(self, exposure_time=None, gain=None, save=True):
        with self._sdk_lock:
            if self.capter is None:
                raise RuntimeError("2D camera is not connected")
            if exposure_time is not None:
                self._set_int(self.capter, "ExposureTime", exposure_time)
            if gain is not None:
                self._set_int(self.capter, "Gain", gain)
            if save:
                self._save_camera_params(self.capter)

    def _get_frame_once(self, cam, timeout_ms=1000):
        if self.payload_size <= 0:
            self._read_image_shape(cam)
        st_out_frame = MV_FRAME_OUT_INFO_EX()
        p_data = (c_ubyte * int(self.payload_size))()
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

    def get_status(self):
        with self._state_lock:
            last_frame_time = self.last_frame_time
            return {
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
            }

    def run(self):
        if not self.yaml_config:
            self._set_state("disabled", "2D camera yaml_config missing", connected=False)
            logger.error("2D camera yaml_config missing, capture thread not started")
            return

        reconnect_delay = 1

        while True:
            cam = None
            try:
                self._reconnect_event.clear()
                self.connect_attempts += 1
                with self._sdk_lock:
                    self._set_state("connecting", connected=False)
                    self.capter = None
                cam = self._create_camera()
                with self._sdk_lock:
                    self.capter = cam
                    self.last_connect_time = time.time()
                    self._set_state("streaming", "", connected=True)
                self._clear_queue()
                reconnect_delay = 1
                last_wait_log = 0
                while True:
                    if self._reconnect_event.is_set():
                        raise RuntimeError("Manual reconnect requested")
                    with self._sdk_lock:
                        frame, ret = self._get_frame_once(cam, timeout_ms=1000)
                    now = time.time()
                    if frame is None:
                        self.empty_frame_count += 1
                        self._set_state("waiting_trigger", "", connected=True)
                        if now - last_wait_log >= 60:
                            logger.debug(
                                f"2D camera {self.camera_key} waiting external trigger "
                                f"(no image, ret=0x{ret:08X}, empty={self.empty_frame_count})"
                            )
                            last_wait_log = now
                        continue
                    self.empty_frame_count = 0
                    self.frame_error_count = 0
                    self.last_frame_time = now
                    self.frame_id += 1
                    self._set_state("streaming", "", connected=True)
                    self._put_latest_frame(frame, now)
            except BaseException as e:
                with self._sdk_lock:
                    self.capter = None
                    self.last_disconnect_time = time.time()
                    self._set_state("reconnecting", e, connected=False)
                logger.warning(f"2D camera {self.camera_key} disconnected, retrying in {reconnect_delay}s: {e}")
                self._clear_queue()
                self._safe_release_camera(cam)
                time.sleep(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 2, 5)
