import importlib.util
import logging
import sys
from pathlib import Path
from threading import Event
from types import ModuleType, SimpleNamespace

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CAPTRUE_ROOT = PROJECT_ROOT / "app" / "CapTrue"


def load_capture_module(monkeypatch):

    class CameraConfig:
        pass

    class SecondaryCoil:

        def __init__(self, coil_id):
            self.Id = coil_id

    class DaHengBuffer:

        def __init__(self, area_cap, last_time):
            self.area_cap = area_cap
            self.last_time = last_time
            self.coilData = None
            self.coilId = None

        def setCoil(self, coil):
            self.coilData = coil
            self.coilId = str(coil.Id)

    class SickBuffer:

        def __init__(self, raw_buffer):
            self.raw_buffer = raw_buffer
            self.bd_config = None
            self.coilData = None
            self.coilId = None

        def setBDconfig(self, bd_config):
            self.bd_config = bd_config

        def setCoil(self, coil):
            self.coilData = coil
            self.coilId = str(coil.Id)

    config_module = ModuleType("CONFIG")
    config_module.CameraConfig = CameraConfig
    server_module = ModuleType("Server")
    server_module.start_server = lambda *args, **kwargs: None
    camera_module = ModuleType("Camera")
    camera_module.DaHengCamera = object
    camera_module.SickCamera = object
    camera_control_module = ModuleType("CameraControl")
    camera_control_module.CameraControl = object

    coil_package = ModuleType("CoilDataBase")
    coil_package.__path__ = []
    models_package = ModuleType("CoilDataBase.models")
    models_package.__path__ = []
    secondary_module = ModuleType("CoilDataBase.models.SecondaryCoil")
    secondary_module.SecondaryCoil = SecondaryCoil

    image_buffer_module = ModuleType("ImageBuffer")
    image_buffer_module.DaHengBuffer = DaHengBuffer
    image_buffer_module.SickBuffer = SickBuffer
    image_data_save_module = ModuleType("ImageDataSave")
    image_data_save_module.CAPTURE_SAVE_JOIN_TIMEOUT = 1
    image_data_save_module.ImageDataSave = object
    log_module = ModuleType("Log")
    log_module.logger = logging.getLogger("test.capture_coil_switch")
    signal_module = ModuleType("Signal")
    signal_module.lastTimeDict = {}
    signal_module.signal = SimpleNamespace(register=lambda callback: None)

    modules = {
        "CONFIG": config_module,
        "Server": server_module,
        "Camera": camera_module,
        "CameraControl": camera_control_module,
        "CoilDataBase": coil_package,
        "CoilDataBase.models": models_package,
        "CoilDataBase.models.SecondaryCoil": secondary_module,
        "ImageBuffer": image_buffer_module,
        "ImageDataSave": image_data_save_module,
        "Log": log_module,
        "Signal": signal_module,
    }
    for name, module in modules.items():
        monkeypatch.setitem(sys.modules, name, module)

    module_name = "capture_coil_switch_test"
    sys.modules.pop(module_name, None)
    spec = importlib.util.spec_from_file_location(
        module_name, CAPTRUE_ROOT / "CapTure.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module, SecondaryCoil


def test_3d_frame_uses_new_coil_when_coil_switches_during_get_buffer(
        monkeypatch):
    module, SecondaryCoil = load_capture_module(monkeypatch)
    buffer_requested = Event()
    release_buffer = Event()
    raw_buffer_queued = Event()
    frame_saved = Event()

    class RawBuffer:

        def queue(self):
            raw_buffer_queued.set()

    class BlockingCamera:

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def get_buffer(self):
            buffer_requested.set()
            if not release_buffer.wait(timeout=2):
                raise TimeoutError("test did not release the 3D buffer")
            return RawBuffer()

        def getBDconfig(self):
            return {"scale": 1}

    old_coil = SecondaryCoil(213231)
    new_coil = SecondaryCoil(213232)
    parent = SimpleNamespace(
        coil=old_coil,
        captureRunning=True,
        last_frame_time_3d=0,
        last_error_3d="",
    )
    saved_buffers = []

    class DataSave:

        capture_thread = None

        def put(self, buffer):
            saved_buffers.append(buffer)
            self.capture_thread.running = False
            frame_saved.set()

    data_save = DataSave()
    capture_thread = module.CapTure3D(
        data_save,
        BlockingCamera(),
        parent,
        SimpleNamespace(key="Cap_S_D"),
    )
    data_save.capture_thread = capture_thread

    try:
        capture_thread.start()
        assert buffer_requested.wait(timeout=2)
        parent.coil = new_coil
        release_buffer.set()

        assert frame_saved.wait(timeout=2)
        capture_thread.join(timeout=2)

        assert not capture_thread.is_alive()
        assert len(saved_buffers) == 1
        assert saved_buffers[0].coilData is new_coil
        assert saved_buffers[0].coilId == "213232"
        assert raw_buffer_queued.is_set()
    finally:
        parent.captureRunning = False
        capture_thread.running = False
        release_buffer.set()
        capture_thread.join(timeout=2)


def test_3d_capture_worker_retries_initial_camera_creation(monkeypatch):
    module, _ = load_capture_module(monkeypatch)
    recovered_camera = object()
    attempts = 0

    def set_camera_3d():
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RuntimeError("DeviceOpen failed")
        return recovered_camera

    parent = SimpleNamespace(
        set_camera_3d=set_camera_3d,
        camera_3d=None,
        coil=None,
        captureRunning=False,
        last_error_3d="",
    )
    capture_thread = module.CapTure3D(
        SimpleNamespace(),
        None,
        parent,
        SimpleNamespace(key="Cap_S_D"),
    )

    with pytest.raises(RuntimeError, match="DeviceOpen"):
        capture_thread._ensure_camera()
    camera = capture_thread._ensure_camera()

    assert camera is recovered_camera
    assert capture_thread.camera is recovered_camera
    assert parent.camera_3d is recovered_camera
    assert attempts == 2


def test_2d_frame_uses_new_coil_when_coil_switches_during_get_last_frame(
        monkeypatch):
    module, SecondaryCoil = load_capture_module(monkeypatch)
    frame_requested = Event()
    release_frame = Event()
    frame_saved = Event()

    class BlockingCamera:

        def get_last_frame(self, timeout):
            frame_requested.set()
            if not release_frame.wait(timeout=2):
                raise TimeoutError("test did not release the 2D frame")
            return "pixels", 123

    old_coil = SecondaryCoil(213231)
    new_coil = SecondaryCoil(213232)
    parent = SimpleNamespace(
        coil=old_coil,
        captureRunning=True,
        last_frame_time_2d=0,
        last_error_2d="",
        missed_in_without_frame=0,
        reconnect_attempts=0,
    )
    saved_buffers = []

    class DataSave:

        capture_thread = None

        def put(self, buffer):
            saved_buffers.append(buffer)
            self.capture_thread.running = False
            frame_saved.set()

    data_save = DataSave()
    capture_thread = module.CapTure2D(
        data_save,
        BlockingCamera(),
        parent,
        SimpleNamespace(key="Cap_S_D"),
    )
    data_save.capture_thread = capture_thread

    try:
        capture_thread.start()
        assert frame_requested.wait(timeout=2)
        parent.coil = new_coil
        release_frame.set()

        assert frame_saved.wait(timeout=2)
        capture_thread.join(timeout=2)

        assert not capture_thread.is_alive()
        assert len(saved_buffers) == 1
        assert saved_buffers[0].coilData is new_coil
        assert saved_buffers[0].coilId == "213232"
    finally:
        parent.captureRunning = False
        capture_thread.running = False
        release_frame.set()
        capture_thread.join(timeout=2)


def test_3d_frame_is_discarded_when_capture_stops_during_get_buffer(
        monkeypatch):
    module, SecondaryCoil = load_capture_module(monkeypatch)
    buffer_requested = Event()
    release_buffer = Event()
    raw_buffer_queued = Event()

    class RawBuffer:

        def queue(self):
            raw_buffer_queued.set()

    class BlockingCamera:

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def get_buffer(self):
            buffer_requested.set()
            if not release_buffer.wait(timeout=2):
                raise TimeoutError("test did not release the 3D buffer")
            return RawBuffer()

        def getBDconfig(self):
            return {"scale": 1}

    parent = SimpleNamespace(
        coil=SecondaryCoil(213231),
        captureRunning=True,
        last_frame_time_3d=0,
        last_error_3d="",
    )
    saved_buffers = []
    data_save = SimpleNamespace(put=saved_buffers.append)
    capture_thread = module.CapTure3D(
        data_save,
        BlockingCamera(),
        parent,
        SimpleNamespace(key="Cap_S_D"),
    )

    try:
        capture_thread.start()
        assert buffer_requested.wait(timeout=2)
        parent.captureRunning = False
        capture_thread.running = False
        release_buffer.set()
        capture_thread.join(timeout=2)

        assert not capture_thread.is_alive()
        assert saved_buffers == []
        assert raw_buffer_queued.is_set()
    finally:
        parent.captureRunning = False
        capture_thread.running = False
        release_buffer.set()
        capture_thread.join(timeout=2)
