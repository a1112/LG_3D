import importlib.util
import gc
import sys
import time
import weakref
from pathlib import Path
from types import ModuleType, SimpleNamespace

import numpy as np
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[1]
IMAGE_SAVER_PATH = (PROJECT_ROOT / "app" / "algorithm_runtime" /
                    "SplicingService" / "ImageSaver.py")


class _Logger:

    def __getattr__(self, _name):
        return lambda *args, **kwargs: None


def _load_image_saver(monkeypatch, save_numpy, save_image=None):
    globs = ModuleType("Globs")
    globs.control = SimpleNamespace(
        ImageSaverWorkNum=1,
        ImageSaverThreadType="threading",
        ImageSaverQueueSize=4,
    )
    storage = ModuleType("Base.tools.compressed_storage")
    storage.save_compressed_image = save_image or (lambda image, path: None)
    storage.save_compressed_numpy = save_numpy
    log = ModuleType("Base.utils.Log")
    log.logger = _Logger()
    monkeypatch.setitem(sys.modules, "Globs", globs)
    monkeypatch.setitem(sys.modules, "Base.tools.compressed_storage", storage)
    monkeypatch.setitem(sys.modules, "Base.utils.Log", log)

    module_name = "test_image_saver_module"
    spec = importlib.util.spec_from_file_location(module_name,
                                                  IMAGE_SAVER_PATH)
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, module_name, module)
    spec.loader.exec_module(module)
    return module


def test_flush_waits_for_queued_save(monkeypatch, tmp_path):
    saved_paths = []

    def save_numpy(array, path):
        assert np.array_equal(array, np.array([1, 2, 3]))
        saved_paths.append(Path(path))

    module = _load_image_saver(monkeypatch, save_numpy)
    saver = module.ImageSaver(None, None)
    output = tmp_path / "3D.npz"

    assert saver.add_numpy(np.array([1, 2, 3]), output)
    assert saver.flush(timeout=1)
    assert saved_paths == [output]
    saver.join()


def test_flush_reports_worker_failure(monkeypatch, tmp_path):

    def fail_save(_array, _path):
        raise OSError("disk full")

    module = _load_image_saver(monkeypatch, fail_save)
    saver = module.ImageSaver(None, None)

    assert saver.add_numpy(np.array([1]), tmp_path / "3D.npz")
    assert not saver.flush(timeout=1)
    saver.join()


def test_image_tasks_use_private_pillow_copies(monkeypatch, tmp_path):
    original = Image.fromarray(np.full((4, 4), 100, dtype=np.uint8))
    worker_saw_original = []

    def save_image(image, _path):
        worker_saw_original.append(image is original)

    module = _load_image_saver(monkeypatch, lambda array, path: None,
                               save_image)
    saver = module.ImageSaver(None, None)

    assert saver.add_image(original, tmp_path / "GRAY.jpg")
    assert saver.flush(timeout=1)
    assert worker_saw_original == [False]
    assert np.array(original).mean() == 100
    saver.join()


def test_acknowledgements_are_reclaimed_during_long_runs(monkeypatch,
                                                         tmp_path):
    module = _load_image_saver(monkeypatch, lambda array, path: None)
    saver = module.ImageSaver(None, None)

    for index in range(50):
        assert saver.add_numpy(np.array([index]),
                               tmp_path / f"{index}.npz")

    deadline = time.monotonic() + 2
    while saver._pending_task_ids and time.monotonic() < deadline:
        time.sleep(0.01)

    assert saver._pending_task_ids == set()
    assert saver.ack_queue.maxsize == 4
    assert saver.flush(timeout=1)
    saver.join()


def test_idle_save_worker_releases_last_numpy_payload(monkeypatch, tmp_path):
    module = _load_image_saver(monkeypatch, lambda array, path: None)
    saver = module.ImageSaver(None, None)
    payload = np.ones((32, 32), dtype=np.uint16)
    payload_ref = weakref.ref(payload)

    assert saver.add_numpy(payload, tmp_path / "3D.npz")
    assert saver.flush(timeout=1)
    del payload

    deadline = time.monotonic() + 1
    while payload_ref() is not None and time.monotonic() < deadline:
        gc.collect()
        time.sleep(0.01)

    try:
        assert payload_ref() is None
    finally:
        saver.join()
