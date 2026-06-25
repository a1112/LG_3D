import logging
import time
from threading import Thread

try:
    import yaml
except ImportError:
    yaml = None

import CONFIG

try:
    from Log import logger
except ImportError:  # pragma: no cover - used by isolated unit tests
    logger = logging.getLogger(__name__)


class CameraControl(Thread):
    def __init__(self, capTrue):
        super().__init__()
        self.capTrue = capTrue

    def _camera_2d(self):
        return getattr(self.capTrue, "camera_2d", None)

    def _camera_config_path(self):
        camera = self._camera_2d()
        yaml_config = getattr(camera, "yaml_config", None)
        if not yaml_config:
            return None
        return CONFIG.CONFIG_DIR / yaml_config

    def _camera_config_params(self):
        config_path = self._camera_config_path()
        if yaml is None or config_path is None or not config_path.exists():
            return {}
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            camera_config = data.get("cameraConfig", {})
            return {
                "exposureTime": camera_config.get("exposureTime"),
                "gain": camera_config.get("gain"),
            }
        except Exception as e:
            logger.debug("2D camera config params read failed: %s", e)
            return {}

    def _live_capter(self):
        camera = self._camera_2d()
        if camera is None:
            return None
        if not getattr(camera, "connected", False):
            return None
        return getattr(camera, "capter", None)

    def _read_live_params(self, capter):
        params = {}
        sdk = getattr(capter, "sdk", None)
        if sdk is None:
            return params
        try:
            params["exposureTime"] = int(sdk.exposureTime)
        except Exception as e:
            params["exposureError"] = str(e)
        try:
            params["gain"] = int(sdk.gain)
        except Exception as e:
            params["gainError"] = str(e)
        return params

    def get_2d_status(self):
        camera = self._camera_2d()
        config_params = self._camera_config_params()
        status = {
            "ok": True,
            "cameraKey": getattr(getattr(self.capTrue, "cameraInfo", None), "key", ""),
            "cameraName": getattr(getattr(self.capTrue, "cameraInfo", None), "name", ""),
            "yamlConfig": getattr(camera, "yaml_config", None),
            "paramFile": str(getattr(camera, "camera_param_file", "") or ""),
            "cap2D": camera is not None,
            "connected": False,
            "writable": False,
            "lastFrameTime": getattr(camera, "last_frame_time", 0) if camera else 0,
            "lastFrameAge": None,
            "queueSize": None,
            "params": config_params,
            "source": "config",
            "message": getattr(camera, "last_error", "") if camera else "",
        }
        if camera is None:
            status["ok"] = False
            status["message"] = "2D camera is not enabled"
            return status

        last_frame_time = getattr(camera, "last_frame_time", 0) or 0
        if last_frame_time:
            status["lastFrameAge"] = max(time.time() - last_frame_time, 0)

        try:
            status["queueSize"] = camera.frame_queue.qsize()
        except Exception as e:
            logger.debug("2D camera queue size read failed: %s", e)
            status["queueSize"] = None

        if hasattr(camera, "get_status"):
            try:
                status.update(camera.get_status())
            except Exception as e:
                logger.debug("2D camera status read failed: %s", e)
                status["message"] = str(e)

        capter = self._live_capter()
        status["connected"] = capter is not None
        status["writable"] = capter is not None
        if capter is None:
            status["ok"] = False
            if not status["message"]:
                status["message"] = "2D camera is not connected"
            return status

        status["source"] = "camera"
        live_params = self._read_live_params(capter)
        if live_params:
            status["params"] = live_params
        return status

    def set_2d_params(self, exposure_time=None, gain=None, save=True):
        camera = self._camera_2d()
        if camera is None:
            raise RuntimeError("2D camera is not enabled")
        if hasattr(camera, "set_params"):
            camera.set_params(exposure_time=exposure_time, gain=gain, save=save)
            return self.get_2d_status()

        capter = self._live_capter()
        if capter is None:
            raise RuntimeError("2D camera is not connected")
        sdk = getattr(capter, "sdk", None)
        if sdk is None:
            raise RuntimeError("2D camera SDK is not available")

        with camera._sdk_lock:
            if exposure_time is not None:
                sdk.exposureTime = int(exposure_time)
            if gain is not None:
                sdk.gain = int(gain)
            if save:
                camera._save_camera_params(capter)
        return self.get_2d_status()

    def reconnect_2d(self):
        camera = self._camera_2d()
        if camera is None:
            raise RuntimeError("2D camera is not enabled")
        camera.request_reconnect()
        return self.get_2d_status()
