import os
import socket
import time
from threading import Thread
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn


class CameraParamsPayload(BaseModel):
    exposureTime: Optional[int] = None
    gain: Optional[int] = None
    save: bool = True


class CameraServer(Thread):
    def __init__(self, camera_info, cap):
        super().__init__()
        self.cameraInfo = camera_info
        self.cap = cap

    def run(self):
        app = FastAPI()

        @app.get("/getListenerAddFile")
        def get_listener_add_file():
            return self.cap.getCreatedFile()

        @app.get("/camera/status")
        def get_camera_status():
            try:
                return self.cap.cameraControl.get_2d_status()
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @app.post("/camera/params")
        def set_camera_params(payload: CameraParamsPayload):
            try:
                return self.cap.cameraControl.set_2d_params(
                    exposure_time=payload.exposureTime,
                    gain=payload.gain,
                    save=payload.save,
                )
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))

        @app.post("/camera/reconnect")
        def reconnect_camera():
            try:
                return self.cap.cameraControl.reconnect_2d()
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))

        uvicorn.run(
            app,
            host=self.cameraInfo.serverIp,
            port=self.cameraInfo.serverPort,
            log_config=None,
        )


def start_server(camera_info, cap):
    CameraServer(camera_info, cap).start()


def _cap_status(cap):
    try:
        return cap.get_capture_status()
    except Exception as e:
        return {
            "key": getattr(getattr(cap, "cameraInfo", None), "key", ""),
            "ok": False,
            "message": str(e),
        }


def _cap_liveness(cap):
    try:
        get_liveness = getattr(cap, "get_liveness_status", None)
        if not callable(get_liveness):
            return {
                "ok": True,
                "requiresProcessRestart": False,
                "stalledComponents": [],
            }
        return get_liveness()
    except Exception as e:
        # A health snapshot is deliberately no-I/O. If even this fails, the
        # process is internally inconsistent and the external watchdog is the
        # only safe recovery boundary.
        return {
            "ok": False,
            "requiresProcessRestart": True,
            "stalledComponents": ["livenessSnapshot"],
            "message": str(e),
        }


class CaptureApiServer(Thread):
    def __init__(self, capture_config, cap_map, signal_listener=None):
        super().__init__()
        self.capture_config = capture_config
        self.cap_map = cap_map
        self.signal_listener = signal_listener

    def _get_cap(self, camera_key):
        cap = self.cap_map.get(camera_key)
        if cap is None:
            raise HTTPException(status_code=404, detail=f"camera not found: {camera_key}")
        return cap

    def _all_status(self):
        cameras = [_cap_status(cap) for cap in self.cap_map.values()]
        healthy_cameras = [item for item in cameras if _camera_ok(item)]
        failed_cameras = [item for item in cameras if not _camera_ok(item)]
        has_healthy_camera = bool(healthy_cameras)
        return {
            # `ok` describes whether the capture service still has usable
            # cameras. Per-camera failures remain visible through `degraded`,
            # `allCamerasOk`, and the detailed camera status list.
            "ok": has_healthy_camera,
            "degraded": bool(failed_cameras) and has_healthy_camera,
            "allCamerasOk": bool(cameras) and not failed_cameras,
            "service": "CapAll",
            "processId": os.getpid(),
            "watchdogToken": os.getenv("LG3D_CAPTURE_WATCHDOG_TOKEN", ""),
            "time": time.time(),
            "configFile": getattr(self.capture_config, "config_file", ""),
            "apiServerIp": getattr(self.capture_config, "apiServerIp", "0.0.0.0"),
            "apiServerPort": getattr(self.capture_config, "apiServerPort", 6100),
            "cameraCount": len(cameras),
            "healthyCameraCount": len(healthy_cameras),
            "failedCameraCount": len(failed_cameras),
            "failedCameraKeys": [item.get("key", "") for item in failed_cameras],
            "cameras": cameras,
        }

    def _all_liveness(self):
        cameras = {
            key: _cap_liveness(cap)
            for key, cap in self.cap_map.items()
        }
        restart_keys = [
            key for key, status in cameras.items()
            if status.get("requiresProcessRestart", False)
        ]
        signal_status = None
        signal_requires_restart = False
        if self.signal_listener is not None:
            try:
                signal_status = self.signal_listener.get_status()
                signal_requires_restart = bool(signal_status.get("stalled"))
                if (getattr(self.signal_listener, "ident", None) is not None
                        and not signal_status.get("alive", False)):
                    signal_requires_restart = True
            except Exception as e:
                signal_status = {
                    "alive": False,
                    "stalled": True,
                    "message": str(e),
                }
                signal_requires_restart = True
        requires_restart = bool(restart_keys or signal_requires_restart)
        return {
            "ok": not requires_restart,
            "service": "CapAll",
            "processId": os.getpid(),
            "watchdogToken": os.getenv("LG3D_CAPTURE_WATCHDOG_TOKEN", ""),
            "time": time.time(),
            "requiresProcessRestart": requires_restart,
            "restartCameraKeys": restart_keys,
            "signalRequiresProcessRestart": signal_requires_restart,
            "signal": signal_status,
            "cameras": cameras,
        }

    def run(self):
        app = FastAPI(title="LG 3D Capture API")

        @app.get("/health")
        def health():
            return self._all_liveness()

        @app.get("/capture/liveness")
        def capture_liveness():
            return self._all_liveness()

        @app.get("/capture/status")
        def capture_status():
            return self._all_status()

        @app.get("/capture/files")
        def capture_files(clear: bool = False):
            return {
                key: cap.getCreatedFile(clear=clear)
                for key, cap in self.cap_map.items()
            }

        @app.get("/getListenerAddFile")
        def get_listener_add_file(clear: bool = False):
            return capture_files(clear=clear)

        @app.get("/cameras")
        def get_cameras():
            return {
                "ok": True,
                "cameras": [_cap_status(cap) for cap in self.cap_map.values()],
            }

        @app.get("/cameras/{camera_key}/status")
        def get_camera_status(camera_key: str):
            return _cap_status(self._get_cap(camera_key))

        @app.get("/cameras/{camera_key}/files")
        def get_camera_files(camera_key: str, clear: bool = False):
            return self._get_cap(camera_key).getCreatedFile(clear=clear)

        @app.post("/cameras/{camera_key}/params")
        def set_camera_params(camera_key: str, payload: CameraParamsPayload):
            cap = self._get_cap(camera_key)
            try:
                return cap.cameraControl.set_2d_params(
                    exposure_time=payload.exposureTime,
                    gain=payload.gain,
                    save=payload.save,
                )
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))

        @app.post("/cameras/{camera_key}/reconnect")
        def reconnect_camera(camera_key: str):
            cap = self._get_cap(camera_key)
            try:
                return cap.cameraControl.reconnect_2d()
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))

        @app.post("/cameras/{camera_key}/reconnect/2d")
        def reconnect_camera_2d(camera_key: str):
            cap = self._get_cap(camera_key)
            try:
                return cap.cameraControl.reconnect_2d()
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))

        @app.post("/cameras/{camera_key}/reconnect/3d")
        def reconnect_camera_3d(camera_key: str):
            try:
                return self._get_cap(camera_key).reconnect_3d()
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))

        @app.post("/cameras/{camera_key}/reset/3d")
        def reset_camera_3d(camera_key: str):
            try:
                return self._get_cap(camera_key).reset_3d()
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))

        uvicorn.run(
            app,
            host=getattr(self.capture_config, "apiServerIp", "0.0.0.0"),
            port=getattr(self.capture_config, "apiServerPort", 6100),
            log_config=None,
        )


def _camera_ok(status):
    if not status.get("serviceReady", False):
        return False
    save_worker = status.get("saveWorker") or {}
    if save_worker.get("lastSaveError"):
        return False
    if status.get("cap3D"):
        camera_3d = status.get("camera3D") or {}
        if not camera_3d.get("ok", False):
            return False
        if status.get("lastError3D"):
            return False
    if status.get("cap2D"):
        camera_2d = status.get("camera2D") or {}
        if not camera_2d.get("ok", False):
            return False
    return True


def _assert_api_port_available(host: str, port: int) -> None:
    bind_host = host or "0.0.0.0"
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind((bind_host, int(port)))


def start_capture_api(capture_config,
                      cap_map,
                      signal_listener=None,
                      startup_probe_seconds: float = 0.5):
    host = getattr(capture_config, "apiServerIp", "0.0.0.0")
    port = int(getattr(capture_config, "apiServerPort", 6100))
    _assert_api_port_available(host, port)

    server = CaptureApiServer(capture_config, cap_map, signal_listener)
    server.start()
    deadline = time.monotonic() + max(float(startup_probe_seconds), 0.1)
    while time.monotonic() < deadline:
        if not server.is_alive():
            raise RuntimeError(
                f"capture API stopped during startup on {host}:{port}")
        time.sleep(0.05)
    return server
