import importlib.util
import sys
from pathlib import Path
from types import ModuleType


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CAPTRUE_ROOT = PROJECT_ROOT / "app" / "CapTrue"


def load_image_buffer(monkeypatch):
    harvesters_module = ModuleType("harvesters")
    harvesters_core = ModuleType("harvesters.core")

    class Buffer:
        pass

    class SecondaryCoil:
        pass

    harvesters_core.Buffer = Buffer
    secondary_module = ModuleType("CoilDataBase.models.SecondaryCoil")
    secondary_module.SecondaryCoil = SecondaryCoil
    monkeypatch.setitem(sys.modules, "harvesters", harvesters_module)
    monkeypatch.setitem(sys.modules, "harvesters.core", harvesters_core)
    monkeypatch.setitem(sys.modules, "CoilDataBase.models.SecondaryCoil", secondary_module)
    sys.modules.pop("ImageBuffer", None)

    spec = importlib.util.spec_from_file_location("ImageBuffer", CAPTRUE_ROOT / "ImageBuffer.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["ImageBuffer"] = module
    spec.loader.exec_module(module)
    return module


def test_buffer_base_accepts_placeholder_coil_id(monkeypatch):
    module = load_image_buffer(monkeypatch)
    buffer = module.BufferBase()

    buffer.setCoil(1)

    assert buffer.coilId == "1"
    assert buffer.coilData is None


def test_buffer_base_keeps_real_coil_object(monkeypatch):
    module = load_image_buffer(monkeypatch)
    buffer = module.BufferBase()

    class Coil:
        Id = 205001

        def get_json(self):
            return {"Id": self.Id}

    coil = Coil()
    buffer.setCoil(coil)

    assert buffer.coilId == "205001"
    assert buffer.coilData is coil


def test_capture_save_worker_has_bounded_queue_and_exception_guard():
    source = (CAPTRUE_ROOT / "ImageDataSave.py").read_text(encoding="utf-8")

    assert "timeout=CAPTURE_SAVE_QUEUE_PUT_TIMEOUT" in source
    assert "except Full:" in source
    assert "capture save worker failed" in source
    assert "def _save_array_image" in source
    assert "image.close()" in source
    assert "skip capture database log without coil object" in source
    assert "def stop(self)" in source
    assert "self.queue.put(None" in source


def test_capture_loop_requires_active_coil_before_saving():
    source = (CAPTRUE_ROOT / "CapTure.py").read_text(encoding="utf-8")

    assert "def get_active_coil" in source
    assert "not self.parent.captureRunning or coil is None" in source
    assert "if coil is None:" in source
    assert "continue" in source
    assert "self.capture_threads" in source
    assert "def release(self)" in source
    assert "capture_thread.join(timeout=2)" in source
