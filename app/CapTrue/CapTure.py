import os
import time
from pathlib import Path
from threading import Event, Lock, Thread
from typing import Any

import CONFIG
import Server
from Camera import DaHengCamera, SickCamera
from CameraControl import CameraControl
from CoilDataBase.models.SecondaryCoil import SecondaryCoil
from ImageBuffer import DaHengBuffer, SickBuffer
from ImageDataSave import CAPTURE_SAVE_JOIN_TIMEOUT, ImageDataSave
from Log import logger
from Signal import lastTimeDict, signal


CAPTURE_NATIVE_OPERATION_STALL_SECONDS = max(
    1.0,
    float(os.getenv("LG3D_CAPTURE_NATIVE_OPERATION_STALL_SECONDS", "30.0")),
)
CAPTURE_CAMERA_JOIN_TIMEOUT = max(
    0.1, float(os.getenv("LG3D_CAPTURE_CAMERA_JOIN_TIMEOUT", "3.0")))
CAPTURE_WORKER_START_STALL_SECONDS = max(
    1.0,
    float(os.getenv("LG3D_CAPTURE_WORKER_START_STALL_SECONDS", "60.0")),
)
CAPTURE_3D_RETRY_MAX_DELAY = max(
    1.0, float(os.getenv("LG3D_CAPTURE_3D_RETRY_MAX_DELAY", "30.0")))
CAPTURE_3D_RETRY_STABLE_SECONDS = max(
    1.0, float(os.getenv("LG3D_CAPTURE_3D_RETRY_STABLE_SECONDS", "30.0")))


class CapTureBase(Thread):

    def __init__(self, dataSave: ImageDataSave, camera, parent, cameraInfo):
        self.parent = parent
        self.camera = camera
        self.dataSave = dataSave
        self.cameraInfo = cameraInfo
        self.running = True
        self._last_empty_coil_log_time = 0.0
        super().__init__()
        self.daemon = True

    def _get_active_coil_snapshot(self):
        coil = self.parent.coil
        if not self.parent.captureRunning or coil is None:
            return None
        return coil

    def get_active_coil(self):
        coil = self._get_active_coil_snapshot()
        if coil is None:
            now = time.time()
            if now - self._last_empty_coil_log_time >= 5:
                logger.debug(
                    "capture idle: camera=%s capture_running=%s has_coil=%s",
                    self.cameraInfo.key,
                    self.parent.captureRunning,
                    self.parent.coil is not None,
                )
                self._last_empty_coil_log_time = now
            time.sleep(0.1)
            return None
        return coil


class CapTure2D(CapTureBase):

    def __init__(self, dataSave: ImageDataSave, camera, parent, cameraInfo):
        super().__init__(dataSave, camera, parent, cameraInfo)

    def run(self):
        while self.running:
            area_cap = None
            bf = None
            coil = None
            try:
                if self.get_active_coil() is None:
                    continue
                try:
                    area_cap, last_time = self.camera.get_last_frame(timeout=2)
                except TimeoutError:
                    camera_status = self.camera.get_status() if hasattr(
                        self.camera, "get_status") else {}
                    if camera_status.get("connected", False):
                        self.parent.last_error_2d = ""
                    else:
                        self.parent.last_error_2d = camera_status.get(
                            "lastError", "2D camera disconnected")
                    time.sleep(0.05)
                    continue

                # A frame wait can span a coil switch; bind at arrival time.
                coil = self._get_active_coil_snapshot()
                if coil is None:
                    continue
                bf = DaHengBuffer(area_cap, last_time)
                bf.setCoil(coil)
                self.dataSave.put(bf)
                lastTimeDict[self.cameraInfo.key] = time.time()
                self.parent.last_frame_time_2d = time.time()
                self.parent.last_error_2d = ""
                self.parent.missed_in_without_frame = 0
                self.parent.reconnect_attempts = 0
            except Exception as e:
                self.parent.last_error_2d = str(e)
                logger.exception("2D capture loop failed: camera=%s error=%s",
                                 self.cameraInfo.key, e)
                time.sleep(5)


class CapTure3D(CapTureBase):

    def __init__(self, dataSave: ImageDataSave, camera, parent, cameraInfo):
        super().__init__(dataSave, camera, parent, cameraInfo)
        self._retry_event = Event()
        self._operation_lock = Lock()
        self._operation_name = ""
        self._operation_started_at = 0.0
        self._operation_started_monotonic = 0.0
        self.retry_failures = 0
        self.retry_delay = 1.0

    def _begin_operation(self, name):
        with self._operation_lock:
            self._operation_name = str(name)
            self._operation_started_at = time.time()
            self._operation_started_monotonic = time.monotonic()

    def _end_operation(self, name):
        with self._operation_lock:
            if self._operation_name == name:
                self._operation_name = ""
                self._operation_started_at = 0.0
                self._operation_started_monotonic = 0.0

    def get_operation_status(self):
        with self._operation_lock:
            name = self._operation_name
            started_at = self._operation_started_at
            started_monotonic = self._operation_started_monotonic
        age = (max(time.monotonic() - started_monotonic, 0.0)
               if name else None)
        stalled = bool(name and age is not None
                       and age > CAPTURE_NATIVE_OPERATION_STALL_SECONDS)
        return {
            "active": bool(name),
            "name": name,
            "startedAt": started_at,
            "age": age,
            "stallAfter": CAPTURE_NATIVE_OPERATION_STALL_SECONDS,
            "stalled": stalled,
        }

    def _ensure_camera(self):
        if self.camera is not None:
            return self.camera
        operation = "initialize_camera"
        self._begin_operation(operation)
        try:
            camera = self.parent.set_camera_3d()
            if camera is None:
                raise RuntimeError("3D camera is not enabled")
            self.camera = camera
            self.parent.camera_3d = camera
            return camera
        finally:
            self._end_operation(operation)

    def request_retry(self):
        self._retry_event.set()

    def _wait_before_retry(self):
        self.retry_failures += 1
        self._retry_event.wait(timeout=self.retry_delay)
        self._retry_event.clear()
        self.retry_delay = min(self.retry_delay * 2,
                               CAPTURE_3D_RETRY_MAX_DELAY)

    def _mark_stable(self):
        self.retry_failures = 0
        self.retry_delay = 1.0

    def run(self):
        while self.running:
            camera = None
            entered = False
            retry_required = False
            try:
                logger.debug("starting 3D camera loop")
                camera = self._ensure_camera()
                operation = "open_camera"
                self._begin_operation(operation)
                try:
                    cap = camera.__enter__()
                    entered = True
                finally:
                    self._end_operation(operation)
                logger.debug("3D camera opened: %s", camera)
                self.parent.last_error_3d = ""
                connected_monotonic = time.monotonic()
                while self.running:
                    buffer = None
                    bf = None
                    coil = None
                    try:
                        process_pending = getattr(cap,
                                                  "process_pending_actions",
                                                  None)
                        if callable(process_pending):
                            process_pending()
                        if (time.monotonic() - connected_monotonic
                                >= CAPTURE_3D_RETRY_STABLE_SECONDS):
                            self._mark_stable()
                        if self.get_active_coil() is None:
                            continue
                        buffer = cap.get_buffer()
                        refresh_telemetry = getattr(cap,
                                                    "refresh_telemetry", None)
                        if callable(refresh_telemetry):
                            refresh_telemetry()
                        if buffer is None:
                            continue
                        # fetch() can span a coil switch; resolve at arrival.
                        coil = self._get_active_coil_snapshot()
                        if coil is None:
                            continue
                        bf = SickBuffer(buffer)
                        bf.setBDconfig(cap.getBDconfig())
                        bf.setCoil(coil)
                        self.dataSave.put(bf)
                        lastTimeDict[self.cameraInfo.key] = time.time()
                        self.parent.last_frame_time_3d = time.time()
                        self.parent.last_error_3d = ""
                        self._mark_stable()
                    finally:
                        if buffer is not None:
                            operation = "queue_buffer"
                            self._begin_operation(operation)
                            try:
                                buffer.queue()
                            finally:
                                self._end_operation(operation)
            except Exception as e:
                retry_required = True
                self.parent.last_error_3d = str(e)
                logger.exception("3D capture loop failed: camera=%s error=%s",
                                 self.cameraInfo.key, e)
            finally:
                if entered and camera is not None:
                    operation = "close_camera"
                    self._begin_operation(operation)
                    try:
                        camera.__exit__(None, None, None)
                    except Exception as e:
                        logger.warning(
                            "3D camera close failed: camera=%s error=%s",
                            self.cameraInfo.key,
                            e,
                        )
                    finally:
                        self._end_operation(operation)
            if retry_required and self.running:
                self._wait_before_retry()


class CapTure(Thread):

    def __init__(self,
                 camera_info: CONFIG.CameraConfig,
                 start_camera_server=True):
        super().__init__()
        self.cameraControl = None
        self.dataSave = None
        self.camera = None
        self.globCapInfo = None
        self.running = None
        self.saveFolder = None
        self.cameraInfo = None
        self.captureRunning = None
        self.coil = None
        self.camera_3d = None
        self.camera_2d = None
        self.capture_threads = []
        self.camera_info = camera_info
        self.start_camera_server = start_camera_server
        self.last_frame_time_2d = 0
        self.last_frame_time_3d = 0
        self.started_at = time.time()
        self.last_trigger_in_time = 0
        self.last_error_2d = ""
        self.last_error_3d = ""
        self.missed_in_without_frame = 0
        self.reconnect_attempts = 0
        self.service_error = ""
        self._service_ready = False
        self._stop_event = Event()
        self._signal_registered = False
        self._release_lock = Lock()
        self._released = False
        self._run_started_at = 0.0
        self._run_started_monotonic = 0.0

    def set_camera_3d(self):
        if self.cameraInfo.cap3D:
            camera = SickCamera(self.cameraInfo.sn)
            self.camera = camera
            return camera
        return None

    def set_camera_2d(self):
        if self.cameraInfo.cap2D:
            yaml_config = self.cameraInfo.yaml_config
            camera = DaHengCamera(yaml_config, camera_key=self.cameraInfo.key)
            return camera
        return None

    def get_value(self, key, default):
        if key in self.camera_info:
            return self.camera_info[key]
        return default

    def on_signal(self, sig_type, coil):
        coilData: SecondaryCoil
        self.coil = coil
        if sig_type == "init":
            self.dataSave.trigger_init(coil)
            self.captureRunning = True
        elif sig_type == "in":
            self.dataSave.trigger_in(coil)
            self.captureRunning = True
            now = time.time()
            if self.last_frame_time_2d <= self.last_trigger_in_time:
                self.missed_in_without_frame += 1
                logger.warning(
                    "2D camera %s no frame between triggerIn, count=%s",
                    self.cameraInfo.key,
                    self.missed_in_without_frame,
                )
                last_frame_age = now - self.last_frame_time_2d if self.last_frame_time_2d else None
                if (self.missed_in_without_frame >= 10 and self.camera_2d
                        and getattr(self.camera_2d, "connected", False)
                        and (last_frame_age is None or last_frame_age > 120)):
                    self.reconnect_attempts += 1
                    logger.warning(
                        "2D camera %s forcing reconnect after repeated missing frames "
                        "(count=%s, last_frame_age=%s, attempt=%s)",
                        self.cameraInfo.key,
                        self.missed_in_without_frame,
                        last_frame_age,
                        self.reconnect_attempts,
                    )
                    self.camera_2d.request_reconnect()
                    self.missed_in_without_frame = 0
                    if self.reconnect_attempts > 5:
                        logger.error(
                            "2D camera %s exceeded 5 reconnect attempts, keep retrying this camera only",
                            self.cameraInfo.key,
                        )
            else:
                self.missed_in_without_frame = 0
            self.last_trigger_in_time = now
        elif sig_type == "out":
            self.dataSave.trigger_out(coil)
            self.captureRunning = False

    def run(self):
        self._stop_event.clear()
        self._run_started_at = time.time()
        self._run_started_monotonic = time.monotonic()
        try:
            self._run_capture_service()
        except Exception as e:
            self.service_error = str(e)
            logger.exception(
                "camera capture service failed without affecting other cameras: camera=%s error=%s",
                getattr(self.cameraInfo, "key", "") or self.camera_info,
                e,
            )
            self.release()
        finally:
            self._service_ready = False

    def _run_capture_service(self):
        camera_info = CONFIG.CameraConfig(self.camera_info)
        self.cameraInfo = camera_info
        self.saveFolder = Path(camera_info.saveFolder) / camera_info.key
        self.running = True
        self.captureRunning = False
        self.globCapInfo = {}
        self.camera = None
        self.dataSave = ImageDataSave(self.saveFolder)
        self.cameraControl = CameraControl(self)
        self.coil: SecondaryCoil | None = None
        signal.register(self.on_signal)
        self._signal_registered = True

        if self.start_camera_server:
            Server.start_server(camera_info, self)
        logger.debug("capture thread started: %s", self.cameraInfo.key)

        camera_3d = None
        camera_2d = None
        if camera_info.cap3D:
            try:
                camera_3d = self.set_camera_3d()
            except Exception as e:
                self.last_error_3d = str(e)
                logger.exception(
                    "3D camera initialization failed; recovery worker will retry: camera=%s error=%s",
                    self.cameraInfo.key,
                    e,
                )
        if camera_info.cap2D:
            try:
                camera_2d = self.set_camera_2d()
            except Exception as e:
                self.last_error_2d = str(e)
                logger.exception(
                    "2D camera initialization failed: camera=%s error=%s",
                    self.cameraInfo.key,
                    e,
                )
        self.camera_3d = camera_3d
        self.camera_2d = camera_2d

        if camera_2d is not None:
            logger.debug("starting 2D capture: %s", self.cameraInfo.key)
            capture_2d = CapTure2D(self.dataSave, camera_2d, self,
                                   self.cameraInfo)
            self.capture_threads.append(capture_2d)
            capture_2d.start()

        if camera_info.cap3D:
            logger.debug("starting 3D capture: %s", self.cameraInfo.key)
            capture_3d = CapTure3D(self.dataSave, camera_3d, self,
                                   self.cameraInfo)
            self.capture_threads.append(capture_3d)
            capture_3d.start()

        self.service_error = ""
        self._service_ready = True
        while self.running:
            self._stop_event.wait(timeout=1)

    def release(self):
        with self._release_lock:
            if self._released:
                return
            self._released = True
            self.running = False
            self.captureRunning = False
            self._stop_event.set()
            unregister = getattr(signal, "unregister", None)
            if self._signal_registered and callable(unregister):
                unregister(self.on_signal)
                self._signal_registered = False
        for capture_thread in self.capture_threads:
            capture_thread.running = False
            if isinstance(capture_thread, CapTure3D):
                capture_thread.request_retry()
        if self.camera_2d is not None and hasattr(self.camera_2d, "stop"):
            self.camera_2d.stop()
        for capture_thread in self.capture_threads:
            capture_thread.join(timeout=2)
            if capture_thread.is_alive():
                logger.warning(
                    "capture thread did not exit within timeout: camera=%s thread=%s",
                    self.cameraInfo.key,
                    capture_thread.name,
                )
        if (self.camera_2d is not None
                and getattr(self.camera_2d, "ident", None) is not None):
            self.camera_2d.join(timeout=CAPTURE_CAMERA_JOIN_TIMEOUT)
            if self.camera_2d.is_alive():
                logger.warning(
                    "2D SDK worker did not exit within timeout: camera=%s",
                    self.cameraInfo.key,
                )
        if self.dataSave is not None:
            self.dataSave.stop()
            self.dataSave.join(timeout=CAPTURE_SAVE_JOIN_TIMEOUT)
            if self.dataSave.is_alive():
                logger.error(
                    "capture save worker did not exit within %.1fs: camera=%s queue_size=%s",
                    CAPTURE_SAVE_JOIN_TIMEOUT,
                    self.cameraInfo.key,
                    self.dataSave._queue_size(),
                )

    def getCreatedFile(self, clear=False):
        if self.dataSave is None:
            return []
        return self.dataSave.get_created_files(clear=clear)

    def reconnect_3d(self) -> dict:
        if not bool(getattr(self.cameraInfo, "cap3D", False)):
            raise RuntimeError("3D capture is not enabled for this camera")
        if self.camera_3d is None:
            for capture_thread in self.capture_threads:
                if isinstance(capture_thread, CapTure3D):
                    self.last_error_3d = ""
                    capture_thread.request_retry()
                    return {
                        "ok": True,
                        "action": "reconnect3D",
                        "message": "3D camera recovery requested",
                        "camera": None,
                    }
            raise RuntimeError("3D camera recovery worker is not running")
        result = self.camera_3d.request_reconnect()
        for capture_thread in self.capture_threads:
            if isinstance(capture_thread, CapTure3D):
                capture_thread.request_retry()
        self.last_error_3d = ""
        return result

    def reset_3d(self) -> dict:
        if not bool(getattr(self.cameraInfo, "cap3D", False)):
            raise RuntimeError("3D capture is not enabled for this camera")
        if self.camera_3d is None:
            raise RuntimeError("3D camera is not initialized")
        result = self.camera_3d.request_device_reset()
        for capture_thread in self.capture_threads:
            if isinstance(capture_thread, CapTure3D):
                capture_thread.request_retry()
        self.last_error_3d = ""
        return result

    def get_liveness_status(self) -> dict[str, Any]:
        """Return a no-I/O snapshot safe for the watchdog health endpoint."""
        stalled_components = []
        component_status = {}

        initialization_age = None
        if (self.ident is not None and self.is_alive()
                and not self._service_ready and self._run_started_monotonic):
            initialization_age = max(
                time.monotonic() - self._run_started_monotonic, 0.0)
            initialization_status = {
                "active": True,
                "name": "initialize_capture_worker",
                "startedAt": self._run_started_at,
                "age": initialization_age,
                "stallAfter": CAPTURE_WORKER_START_STALL_SECONDS,
                "stalled": initialization_age
                > CAPTURE_WORKER_START_STALL_SECONDS,
            }
            component_status["captureWorker.initialization"] = (
                initialization_status)
            if initialization_status["stalled"]:
                stalled_components.append("captureWorker.initialization")

        if self.camera_2d is not None:
            monitor = getattr(self.camera_2d, "_sdk_monitor", None)
            if monitor is not None and callable(getattr(monitor, "status", None)):
                native_status = monitor.status()
                component_status["camera2D.nativeSdk"] = native_status
                if native_status.get("stalled"):
                    stalled_components.append("camera2D.nativeSdk")

        if self.camera_3d is not None:
            monitor = getattr(self.camera_3d, "_sdk_monitor", None)
            if monitor is not None and callable(getattr(monitor, "status", None)):
                native_status = monitor.status()
                component_status["camera3D.nativeSdk"] = native_status
                if native_status.get("stalled"):
                    stalled_components.append("camera3D.nativeSdk")

        capture_workers = []
        for worker in self.capture_threads:
            worker_type = "3D" if isinstance(worker, CapTure3D) else "2D"
            worker_status = {
                "type": worker_type,
                "alive": worker.is_alive(),
            }
            if isinstance(worker, CapTure3D):
                operation = worker.get_operation_status()
                worker_status["nativeOperation"] = operation
                worker_status["retryFailures"] = worker.retry_failures
                worker_status["retryDelay"] = worker.retry_delay
                component_status["capture3D.nativeOperation"] = operation
                if operation.get("stalled"):
                    stalled_components.append("capture3D.nativeOperation")
            capture_workers.append(worker_status)

        save_status = None
        if self.dataSave is not None:
            get_save_status = getattr(self.dataSave, "get_status", None)
            if callable(get_save_status):
                save_status = get_save_status()
                component_status["saveWorker"] = save_status
                if save_status.get("stalled"):
                    stalled_components.append("saveWorker")

        # Once initialization completed, a silently-dead worker cannot be
        # recovered by joining/restarting a Python Thread. A process restart is
        # safer than opening a second SDK handle next to leaked native state.
        dead_workers = []
        if self._service_ready:
            dead_workers = [
                item["type"] for item in capture_workers if not item["alive"]
            ]
            if (self.camera_2d is not None
                    and getattr(self.camera_2d, "ident", None) is not None
                    and not self.camera_2d.is_alive()):
                dead_workers.append("2D SDK")
            if self.dataSave is not None and not self.dataSave.is_alive():
                dead_workers.append("save")

        requires_restart = bool(stalled_components or dead_workers)
        return {
            "ok": not requires_restart,
            "requiresProcessRestart": requires_restart,
            "stalledComponents": stalled_components,
            "deadWorkers": dead_workers,
            "components": component_status,
            "captureWorkers": capture_workers,
            "saveWorker": save_status,
        }

    def get_capture_status(self) -> dict[str, Any]:
        camera_info = self.cameraInfo or CONFIG.CameraConfig(self.camera_info)
        now = time.time()
        liveness = self.get_liveness_status()
        capture_workers = liveness["captureWorkers"]
        save_worker_alive = bool(self.dataSave and self.dataSave.is_alive())
        expected_workers_alive = all(
            worker["alive"] for worker in capture_workers)
        status = {
            "key":
            camera_info.key,
            "name":
            camera_info.name,
            "sn":
            camera_info.sn,
            "cap2D":
            bool(camera_info.cap2D),
            "cap3D":
            bool(camera_info.cap3D),
            "captureRunning":
            bool(self.captureRunning),
            "startedAt":
            self.started_at,
            "lastFrameTime2D":
            self.last_frame_time_2d,
            "lastFrameAge2D":
            now - self.last_frame_time_2d if self.last_frame_time_2d else None,
            "lastFrameTime3D":
            self.last_frame_time_3d,
            "lastFrameAge3D":
            now - self.last_frame_time_3d if self.last_frame_time_3d else None,
            "lastError2D":
            self.last_error_2d,
            "lastError3D":
            self.last_error_3d,
            "missedInWithoutFrame":
            self.missed_in_without_frame,
            "reconnectAttempts":
            self.reconnect_attempts,
            "coilId":
            getattr(self.coil, "Id", None),
            "coilNo":
            getattr(self.coil, "CoilNo", ""),
            "serviceReady":
            self._service_ready and self.is_alive() and save_worker_alive
            and expected_workers_alive,
            "serviceError":
            self.service_error,
            "saveWorkerAlive":
            save_worker_alive,
            "saveWorker":
            liveness["saveWorker"],
            "captureWorkers":
            capture_workers,
            "requiresProcessRestart":
            liveness["requiresProcessRestart"],
            "stalledComponents":
            liveness["stalledComponents"],
            "deadWorkers":
            liveness["deadWorkers"],
            "camera2D":
            None,
            "camera3D":
            None,
        }
        if self.cameraControl is not None:
            try:
                status["camera2D"] = self.cameraControl.get_2d_status(
                    include_live_params=False)
            except Exception as e:
                status["camera2D"] = {
                    "ok": False,
                    "connected": False,
                    "message": str(e),
                }
        if self.camera_3d is not None:
            try:
                status["camera3D"] = self.camera_3d.get_status()
            except Exception as e:
                status["camera3D"] = {
                    "ok": False,
                    "connected": False,
                    "acquiring": False,
                    "message": str(e),
                }
        return status
