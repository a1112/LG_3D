import importlib.util
import logging
import sys
import time
from pathlib import Path
from types import ModuleType, SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CAPTRUE_ROOT = PROJECT_ROOT / "app" / "CapTrue"


def _module(name, **attributes):
    module = ModuleType(name)
    for key, value in attributes.items():
        setattr(module, key, value)
    return module


def _load_capture_module(monkeypatch):

    class CameraConfig:

        def __init__(self, config):
            for key, value in config.items():
                setattr(self, key, value)
            self.cap2D = bool(getattr(self, "cap2D", False))
            self.cap3D = bool(getattr(self, "cap3D", False))

    class Fake2DCamera:

        def __init__(self, yaml_config, camera_key=None):
            self.yaml_config = yaml_config
            self.camera_key = camera_key
            self.connected = True

        def stop(self):
            self.connected = False

        def get_status(self):
            return {"ok": self.connected, "connected": self.connected}

    class Fake3DCamera:

        def __init__(self, serial_number):
            if serial_number == "missing":
                raise RuntimeError("camera missing")
            self.serial_number = serial_number
            self.connected = True

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def release(self):
            self.connected = False

        def get_status(self):
            return {
                "ok": self.connected,
                "connected": self.connected,
                "acquiring": self.connected,
            }

    class FakeCameraControl:

        def __init__(self, cap):
            self.cap = cap

        def get_2d_status(self, include_live_params=False):
            camera = self.cap.camera_2d
            if camera is None:
                return {"ok": False, "connected": False}
            return camera.get_status()

    class FakeImageDataSave:

        def __init__(self, save_folder):
            self.save_folder = save_folder
            self.running = True

        def is_alive(self):
            return self.running

        def stop(self):
            self.running = False

        def join(self, timeout=None):
            return None

        def _queue_size(self):
            return 0

        def get_created_files(self, clear=False):
            return []

    class SecondaryCoil:
        pass

    config_module = _module("CONFIG", CameraConfig=CameraConfig)
    server_module = _module("Server", start_server=lambda *args: None)
    camera_module = _module(
        "Camera",
        DaHengCamera=Fake2DCamera,
        SickCamera=Fake3DCamera,
    )
    camera_control_module = _module("CameraControl",
                                    CameraControl=FakeCameraControl)
    image_buffer_module = _module("ImageBuffer",
                                  DaHengBuffer=object,
                                  SickBuffer=object)
    image_data_save_module = _module(
        "ImageDataSave",
        CAPTURE_SAVE_JOIN_TIMEOUT=1,
        ImageDataSave=FakeImageDataSave,
    )
    signal = SimpleNamespace(register=lambda callback: None)
    signal_module = _module("Signal", lastTimeDict={"t": 0}, signal=signal)
    log_module = _module(
        "Log", logger=logging.getLogger("test.capture_fault_isolation"))

    coil_package = _module("CoilDataBase")
    coil_package.__path__ = []
    models_package = _module("CoilDataBase.models")
    models_package.__path__ = []
    secondary_module = _module("CoilDataBase.models.SecondaryCoil",
                               SecondaryCoil=SecondaryCoil)

    modules = {
        "CONFIG": config_module,
        "Server": server_module,
        "Camera": camera_module,
        "CameraControl": camera_control_module,
        "ImageBuffer": image_buffer_module,
        "ImageDataSave": image_data_save_module,
        "Signal": signal_module,
        "Log": log_module,
        "CoilDataBase": coil_package,
        "CoilDataBase.models": models_package,
        "CoilDataBase.models.SecondaryCoil": secondary_module,
    }
    for name, module in modules.items():
        monkeypatch.setitem(sys.modules, name, module)

    module_name = "capture_fault_isolation_test_module"
    spec = importlib.util.spec_from_file_location(module_name,
                                                  CAPTRUE_ROOT / "CapTure.py")
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, module_name, module)
    spec.loader.exec_module(module)
    return module


def _wait_until(predicate, timeout=2):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return False


def _camera_config(tmp_path, key, serial_number):
    return {
        "key": key,
        "name": key,
        "sn": serial_number,
        "saveFolder": str(tmp_path),
        "yaml_config": f"{key}.yaml",
        "cap2D": True,
        "cap3D": True,
    }


def test_missing_3d_camera_does_not_stop_healthy_camera(monkeypatch, tmp_path):
    module = _load_capture_module(monkeypatch)
    failed = module.CapTure(
        _camera_config(tmp_path, "Cap_S_D", "missing"),
        start_camera_server=False,
    )
    healthy = module.CapTure(
        _camera_config(tmp_path, "Cap_S_M", "healthy"),
        start_camera_server=False,
    )

    failed.start()
    healthy.start()
    try:
        assert _wait_until(
            lambda: failed._service_ready and healthy._service_ready)
        assert failed.is_alive()
        assert healthy.is_alive()
        assert "camera missing" in failed.last_error_3d
        assert healthy.last_error_3d == ""

        failed_workers = {
            type(worker).__name__: worker.is_alive()
            for worker in failed.capture_threads
        }
        healthy_workers = {
            type(worker).__name__: worker.is_alive()
            for worker in healthy.capture_threads
        }
        assert failed_workers == {"CapTure2D": True, "CapTure3D": True}
        assert healthy_workers == {"CapTure2D": True, "CapTure3D": True}
        assert failed.get_capture_status()["serviceReady"] is True
        assert healthy.get_capture_status()["serviceReady"] is True
    finally:
        failed.release()
        healthy.release()
        failed.join(timeout=2)
        healthy.join(timeout=2)

    assert not failed.is_alive()
    assert not healthy.is_alive()


def _load_server_module(monkeypatch):
    module_name = "capture_server_fault_isolation_test_module"
    spec = importlib.util.spec_from_file_location(module_name,
                                                  CAPTRUE_ROOT / "Server.py")
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, module_name, module)
    spec.loader.exec_module(module)
    return module


def test_capture_status_reports_degraded_service_without_marking_it_dead(
        monkeypatch):
    module = _load_server_module(monkeypatch)
    healthy = SimpleNamespace(get_capture_status=lambda: {
        "key": "Cap_S_M",
        "serviceReady": True,
        "cap2D": False,
        "cap3D": False,
    })
    failed = SimpleNamespace(
        get_capture_status=lambda: {
            "key": "Cap_S_D",
            "serviceReady": True,
            "cap2D": False,
            "cap3D": True,
            "camera3D": None,
            "lastError3D": "camera missing",
        })
    server = module.CaptureApiServer(
        SimpleNamespace(apiServerIp="0.0.0.0", apiServerPort=6100),
        {
            "Cap_S_M": healthy,
            "Cap_S_D": failed
        },
    )

    status = server._all_status()

    assert status["ok"] is True
    assert status["degraded"] is True
    assert status["allCamerasOk"] is False
    assert status["healthyCameraCount"] == 1
    assert status["failedCameraCount"] == 1
    assert status["failedCameraKeys"] == ["Cap_S_D"]


def _load_cap_all_module(monkeypatch):
    config_module = _module("CONFIG")
    capture_module = _module("CapTure", CapTure=object)
    signal_module = _module("Signal", signal=SimpleNamespace())
    server_module = _module("Server")
    log_module = _module("Log",
                         logger=logging.getLogger("test.capture_supervisor"))
    for name, module in {
            "CONFIG": config_module,
            "CapTure": capture_module,
            "Signal": signal_module,
            "Server": server_module,
            "Log": log_module,
    }.items():
        monkeypatch.setitem(sys.modules, name, module)

    module_name = "capture_supervisor_fault_isolation_test_module"
    spec = importlib.util.spec_from_file_location(module_name,
                                                  CAPTRUE_ROOT / "CapAll.py")
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, module_name, module)
    spec.loader.exec_module(module)
    return module


def test_capture_supervisor_starts_remaining_cameras_after_one_start_failure(
        monkeypatch):
    module = _load_cap_all_module(monkeypatch)

    class FakeCapture:

        def __init__(self, key, error=None):
            self.camera_info = {"key": key}
            self.error = error
            self.started = False

        def start(self):
            if self.error is not None:
                raise self.error
            self.started = True

    failed = FakeCapture("Cap_S_D", RuntimeError("start failed"))
    healthy = FakeCapture("Cap_S_M")

    started = module.start_capture_workers([failed, healthy])

    assert failed.started is False
    assert healthy.started is True
    assert started == [healthy]


def test_capture_supervisor_rebuilds_stopped_worker_and_updates_api_map(
        monkeypatch):
    module = _load_cap_all_module(monkeypatch)

    class StoppedCapture:

        ident = 1
        service_error = "worker failed"
        start_camera_server = False
        camera_info = {"key": "Cap_S_D"}

        @staticmethod
        def is_alive():
            return False

    class ReplacementCapture:

        def __init__(self, camera_info, start_camera_server):
            self.camera_info = camera_info
            self.start_camera_server = start_camera_server
            self.started = False

        def start(self):
            self.started = True

    class TwoCycleStopEvent:

        def __init__(self):
            self.calls = 0

        def wait(self, timeout):
            self.calls += 1
            return self.calls > 1

    monkeypatch.setattr(module, "CapTure", ReplacementCapture)
    old_capture = StoppedCapture()
    cap_list = [old_capture]
    cap_map = {"Cap_S_D": old_capture}

    module.supervise_capture_workers(
        cap_list,
        TwoCycleStopEvent(),
        cap_map=cap_map,
        interval=0,
    )

    replacement = cap_list[0]
    assert isinstance(replacement, ReplacementCapture)
    assert replacement.started is True
    assert replacement.start_camera_server is False
    assert cap_map["Cap_S_D"] is replacement
