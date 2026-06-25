from threading import Thread
from typing import Optional
import time

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

        uvicorn.run(app, host=self.cameraInfo.serverIp, port=self.cameraInfo.serverPort)


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


class CaptureApiServer(Thread):
    def __init__(self, capture_config, cap_map):
        super().__init__()
        self.capture_config = capture_config
        self.cap_map = cap_map

    def _get_cap(self, camera_key):
        cap = self.cap_map.get(camera_key)
        if cap is None:
            raise HTTPException(status_code=404, detail=f"camera not found: {camera_key}")
        return cap

    def _all_status(self):
        cameras = [_cap_status(cap) for cap in self.cap_map.values()]
        has_error = any(not _camera_ok(item) for item in cameras)
        return {
            "ok": not has_error,
            "service": "CapAll",
            "time": time.time(),
            "configFile": getattr(self.capture_config, "config_file", ""),
            "apiServerIp": getattr(self.capture_config, "apiServerIp", "0.0.0.0"),
            "apiServerPort": getattr(self.capture_config, "apiServerPort", 6100),
            "cameraCount": len(cameras),
            "cameras": cameras,
        }

    def run(self):
        app = FastAPI(title="LG 3D Capture API")

        @app.get("/health")
        def health():
            return {
                "ok": True,
                "service": "CapAll",
                "time": time.time(),
            }

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

        uvicorn.run(
            app,
            host=getattr(self.capture_config, "apiServerIp", "0.0.0.0"),
            port=getattr(self.capture_config, "apiServerPort", 6100),
        )


def _camera_ok(status):
    if not status.get("serviceReady", False):
        return False
    if status.get("cap3D") and status.get("lastError3D"):
        return False
    if status.get("cap2D"):
        camera_2d = status.get("camera2D") or {}
        if not camera_2d.get("ok", False):
            return False
    return True


def start_capture_api(capture_config, cap_map):
    CaptureApiServer(capture_config, cap_map).start()
