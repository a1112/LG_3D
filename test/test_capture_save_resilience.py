import importlib.util
import gc
import logging
import re
import sys
import time
import weakref
from pathlib import Path
from threading import Event, Thread
from types import ModuleType

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CAPTRUE_ROOT = PROJECT_ROOT / "app" / "CapTrue"
ALGORITHM_ROOT = PROJECT_ROOT / "app" / "algorithm_runtime"
ALGORITHM_2D_ROOT = PROJECT_ROOT / "app" / "algorithm_runtime_2D"


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
    monkeypatch.setitem(sys.modules, "CoilDataBase.models.SecondaryCoil",
                        secondary_module)
    sys.modules.pop("ImageBuffer", None)

    spec = importlib.util.spec_from_file_location(
        "ImageBuffer", CAPTRUE_ROOT / "ImageBuffer.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["ImageBuffer"] = module
    spec.loader.exec_module(module)
    return module


def load_image_data_save(monkeypatch):

    class SecondaryCoil:

        def __init__(self, coil_id):
            self.Id = coil_id

    class SickBuffer:

        def __init__(self, coil_id):
            self.coilId = str(coil_id)
            self.save_index = None

    class DaHengBuffer:

        def __init__(self, coil_id):
            self.coilId = str(coil_id)
            self.save_index = None

    config_module = ModuleType("CONFIG")
    config_module.capTureConfig = []

    coil_package = ModuleType("CoilDataBase")
    coil_package.__path__ = []
    models_package = ModuleType("CoilDataBase.models")
    models_package.__path__ = []
    coil_module = ModuleType("CoilDataBase.Coil")
    coil_module.add_obj = lambda obj: obj
    secondary_module = ModuleType("CoilDataBase.models.SecondaryCoil")
    secondary_module.SecondaryCoil = SecondaryCoil
    capture_log_module = ModuleType("CoilDataBase.models.CapTrueLogItem")
    capture_log_module.CapTrueLogItem = lambda **kwargs: kwargs
    storage_policy_module = ModuleType("CoilDataBase.storage_policy")
    storage_policy_module.should_store_capture_raw_files = lambda: False

    base_package = ModuleType("Base")
    base_package.__path__ = []
    tools_package = ModuleType("Base.tools")
    tools_package.__path__ = []
    compressed_storage_module = ModuleType("Base.tools.compressed_storage")
    compressed_storage_module.save_compressed_image = lambda *args: None
    compressed_storage_module.save_compressed_numpy = lambda *args: None

    image_buffer_module = ModuleType("ImageBuffer")
    image_buffer_module.SickBuffer = SickBuffer
    image_buffer_module.DaHengBuffer = DaHengBuffer
    camera_module = ModuleType("Camera")
    camera_module.SickCamera = object
    log_module = ModuleType("Log")
    log_module.logger = logging.getLogger("test.capture_save")

    modules = {
        "CONFIG": config_module,
        "CoilDataBase": coil_package,
        "CoilDataBase.models": models_package,
        "CoilDataBase.Coil": coil_module,
        "CoilDataBase.models.SecondaryCoil": secondary_module,
        "CoilDataBase.models.CapTrueLogItem": capture_log_module,
        "CoilDataBase.storage_policy": storage_policy_module,
        "Base": base_package,
        "Base.tools": tools_package,
        "Base.tools.compressed_storage": compressed_storage_module,
        "ImageBuffer": image_buffer_module,
        "Camera": camera_module,
        "Log": log_module,
    }
    for name, module in modules.items():
        monkeypatch.setitem(sys.modules, name, module)

    module_name = "capture_image_data_save_test"
    sys.modules.pop(module_name, None)
    spec = importlib.util.spec_from_file_location(
        module_name, CAPTRUE_ROOT / "ImageDataSave.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module, SecondaryCoil, SickBuffer, DaHengBuffer


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
    assert "def stop(self," in source
    assert "self.queue.put(None" in source
    assert "def _resume_capture_indices" in source
    assert "resume capture without overwriting existing frames" in source
    assert "self.index_lock" in source
    assert "CAPTURE_SAVE_STOP_TIMEOUT" in source
    assert "CAPTURE_SAVE_JOIN_TIMEOUT" in source
    assert "while True:" in source
    assert "capture_index_high_water" in source


def test_idle_capture_save_worker_releases_last_buffer(monkeypatch, tmp_path):
    module, _, _, _ = load_image_data_save(monkeypatch)
    saver = module.ImageDataSave(tmp_path / "Cap_S_A")

    class WorkItem:
        def __init__(self):
            self.data2D = np.ones((32, 32), dtype=np.uint8)

    saver.save = lambda _data: []
    item = WorkItem()
    item_ref = weakref.ref(item)
    saver.queue.put(item)

    deadline = time.monotonic() + 1
    while not saver.last_saved_at and time.monotonic() < deadline:
        time.sleep(0.01)
    del item
    deadline = time.monotonic() + 1
    while item_ref() is not None and time.monotonic() < deadline:
        gc.collect()
        time.sleep(0.01)

    try:
        assert item_ref() is None
    finally:
        saver.stop()
        saver.join(timeout=1)


def test_capture_save_worker_drains_full_queue_before_sentinel(
        monkeypatch, tmp_path):
    module, _, _, _ = load_image_data_save(monkeypatch)
    saver = module.ImageDataSave(tmp_path / "Cap_S_A")
    first_started = Event()
    release_first = Event()
    stop_finished = Event()
    saved = []

    class WorkItem:

        def __init__(self, index):
            self.index = index

    def save(work_item):
        if work_item.index == 0:
            first_started.set()
            release_first.wait(timeout=5)
        saved.append(work_item.index)

    saver.save = save
    stop_result = {}
    try:
        saver.queue.put(WorkItem(0))
        assert first_started.wait(timeout=2)
        for index in range(1, 31):
            saver.queue.put(WorkItem(index))

        def stop_worker():
            stop_result["enqueued"] = saver.stop(timeout=2)
            stop_finished.set()

        stopper = Thread(target=stop_worker)
        stopper.start()
        assert not stop_finished.wait(timeout=0.05)
        release_first.set()
        stopper.join(timeout=2)
        saver.join(timeout=2)

        assert stop_result == {"enqueued": True}
        assert not stopper.is_alive()
        assert not saver.is_alive()
        assert saved == list(range(31))
    finally:
        release_first.set()
        if saver.is_alive():
            saver.stop(timeout=0.5)
            saver.join(timeout=2)


def test_capture_index_high_water_survives_coil_switch_before_disk_save(
        monkeypatch, tmp_path):
    module, SecondaryCoil, SickBuffer, DaHengBuffer = load_image_data_save(
        monkeypatch)
    save_folder = tmp_path / "Cap_S_A"
    (save_folder / "A" / "2d").mkdir(parents=True)
    (save_folder / "A" / "2d" / "3.jpg").touch()
    (save_folder / "A" / "area").mkdir(parents=True)
    (save_folder / "A" / "area" / "6.jpg").touch()
    saver = module.ImageDataSave(save_folder)
    saver._queue_buffer = lambda buffer: True

    try:
        coil_a = SecondaryCoil("A")
        coil_b = SecondaryCoil("B")
        saver.trigger_in(coil_a)
        a_3d_first = SickBuffer("A")
        a_2d_first = DaHengBuffer("A")
        saver.put(a_3d_first)
        saver.put(a_2d_first)

        saver.trigger_in(coil_b)
        b_3d = SickBuffer("B")
        b_2d = DaHengBuffer("B")
        saver.put(b_3d)
        saver.put(b_2d)

        saver.trigger_in(coil_a)
        a_3d_second = SickBuffer("A")
        a_2d_second = DaHengBuffer("A")
        saver.put(a_3d_second)
        saver.put(a_2d_second)

        assert (a_3d_first.save_index, a_3d_second.save_index) == (4, 5)
        assert (a_2d_first.save_index, a_2d_second.save_index) == (7, 8)
        assert (b_3d.save_index, b_2d.save_index) == (0, 0)
        assert saver.capture_index_high_water["A"] == (6, 9)
    finally:
        saver.stop(timeout=1)
        saver.join(timeout=2)


def test_capture_save_memory_budget_drops_without_blocking(
        monkeypatch, tmp_path):
    module, _, SickBuffer, _ = load_image_data_save(monkeypatch)
    monkeypatch.setattr(module, "CAPTURE_SAVE_QUEUE_MAX_BYTES", 10)
    saver = module.ImageDataSave(tmp_path / "Cap_S_A")
    save_started = Event()
    release_save = Event()

    def blocked_save(_buffer):
        save_started.set()
        release_save.wait(timeout=2)

    saver.save = blocked_save
    first = SickBuffer("A")
    first.data3D = np.zeros(8, dtype=np.uint8)
    second = SickBuffer("A")
    second.data3D = np.zeros(8, dtype=np.uint8)
    try:
        assert saver.put(first) is True
        assert save_started.wait(timeout=1)
        assert saver.put(second) is False
        status = saver.get_status()
        assert status["queuedBytes"] == 8
        assert status["queueMaxBytes"] == 10
        assert status["droppedBuffers"] == 1
    finally:
        release_save.set()
        saver.stop(timeout=1)
        saver.join(timeout=2)


def test_capture_save_default_byte_budget_is_disabled_but_queue_is_bounded(
        monkeypatch, tmp_path):
    module, _, _, _ = load_image_data_save(monkeypatch)
    saver = module.ImageDataSave(tmp_path / "Cap_S_A")

    try:
        assert module.CAPTURE_SAVE_QUEUE_MAX_BYTES == 0
        assert saver.queue.maxsize == 30
    finally:
        saver.stop(timeout=1)
        saver.join(timeout=2)


def test_capture_loop_requires_active_coil_before_saving():
    source = (CAPTRUE_ROOT / "CapTure.py").read_text(encoding="utf-8")

    assert "def get_active_coil" in source
    assert "not self.parent.captureRunning or coil is None" in source
    assert "if coil is None:" in source
    assert "continue" in source
    assert "self.capture_threads" in source
    assert "def release(self)" in source
    assert "capture_thread.join(timeout=2)" in source
    assert "self.dataSave.stop()" in source
    assert "self.dataSave.join(timeout=CAPTURE_SAVE_JOIN_TIMEOUT)" in source
    assert "if self.dataSave.is_alive():" in source


def test_splicing_savers_have_bounded_shutdown():
    image_saver = (ALGORITHM_ROOT / "SplicingService" /
                   "ImageSaver.py").read_text(encoding="utf-8")
    image_mosaic = (ALGORITHM_ROOT / "SplicingService" /
                    "ImageMosaic.py").read_text(encoding="utf-8")
    data_folder = (ALGORITHM_ROOT / "SplicingService" /
                   "DataFolder.py").read_text(encoding="utf-8")
    d3_saver = (ALGORITHM_ROOT / "Save3D" /
                "save.py").read_text(encoding="utf-8")

    assert "LG3D_IMAGE_SAVE_JOIN_TIMEOUT" in image_saver
    assert "LG3D_D3_SAVE_JOIN_TIMEOUT" in d3_saver
    assert "process.join(timeout=self.join_timeout)" in image_saver
    assert "process.join(timeout=self.join_timeout)" in d3_saver
    assert "worker did not exit within" in image_saver
    assert "worker did not exit within" in d3_saver
    assert "self.queue.join()" not in image_saver
    assert "self.queue.join()" not in d3_saver
    assert "if work_item is None:" in data_folder
    assert "def stop(self):" in data_folder
    assert "data_folder.stop()" in image_mosaic
    assert "data_folder.join(timeout=5)" in image_mosaic
    assert "self.join(timeout=shutdown_timeout)" in image_mosaic


def test_image_mosaic_queue_puts_are_bounded():
    source = (ALGORITHM_ROOT / "SplicingService" /
              "ImageMosaic.py").read_text(encoding="utf-8")

    assert "LG3D_MOSAIC_QUEUE_PUT_TIMEOUT" in source
    assert "LG3D_MOSAIC_RESULT_TIMEOUT" in source
    assert '"secondary_coil": secondary_coil' in source
    assert 'current_secondary_coil = work_item.get("secondary_coil")' in source
    assert "self.producer.put(None, timeout=self.queue_put_timeout)" in source
    assert re.search(
        r"self\.consumer\.put\(\s*data_integration,\s*timeout=self\.queue_put_timeout\s*\)",
        source,
    )
    assert "self.consumer.get(timeout=remaining)" in source
    assert "expected_coil_id" in source
    assert "drop mismatched mosaic result" in source
    assert "ImageMosaic producer queue full" in source
    assert "ImageMosaic stop signal queue full" in source
    assert "ImageMosaic consumer queue full" in source


def test_image_mosaic_creates_source_links_before_loading_capture_data():
    source = (ALGORITHM_ROOT / "SplicingService" /
              "ImageMosaic.py").read_text(encoding="utf-8")
    get_all_data = source[source.index("def __getAllData__"):source.index(
        "def _ensure_source_links")]

    assert "def _ensure_source_links" in source
    assert get_all_data.index(
        "self._ensure_source_links(data_integration.coilId)") < (
            get_all_data.index("self._get_capture_frame_plans"))

    data_folder = (ALGORITHM_ROOT / "SplicingService" /
                   "DataFolder.py").read_text(encoding="utf-8")
    assert "link_path.symlink_to(target, target_is_directory=True)" in data_folder
    assert "link_path.exists() or link_path.is_symlink()" in data_folder


def test_image_mosaic_thread_handles_result_timeout():
    source = (ALGORITHM_ROOT / "SplicingService" /
              "ImageMosaicThread.py").read_text(encoding="utf-8")

    assert "except TimeoutError as e:" in source
    assert "image mosaic result timeout" in source
    assert 'status[imageMosaic.key] = ErrorMap["DataFolderError"]' in source
    assert "no image mosaic data available" in source
    assert "processing_error" in source
    assert "image processing failed" in source
    assert "imageMosaic.currentSecondaryCoil = secondary_coil" not in source
    assert "secondary_coil=secondary_coil" in source


def test_2d_recovery_scans_newest_first_with_500_coil_cap():
    server = (ALGORITHM_2D_ROOT / "server.py").read_text(encoding="utf-8")
    main2d = (ALGORITHM_2D_ROOT / "main2d.py").read_text(encoding="utf-8")
    t_main = (ALGORITHM_2D_ROOT / "t_main.py").read_text(encoding="utf-8")
    join_config = (ALGORITHM_2D_ROOT / "configs" /
                   "JoinConfig.py").read_text(encoding="utf-8")

    assert "MAX_RECOVERY_COILS = 500" in server
    assert '"scanDirection": "new_to_old"' in server
    assert '"scanLimit": _bounded_int_env("ALG_2D_AUTO_SCAN_LIMIT", MAX_RECOVERY_COILS, max_value=MAX_RECOVERY_COILS)' in server
    assert '"liveScanLimit": _bounded_int_env("ALG_2D_LIVE_SCAN_LIMIT", 5, max_value=MAX_RECOVERY_COILS)' in server
    assert '"historyScanDone": False' in server
    assert 'scanner_stats["lastScanMode"] = "history_init"' in server
    assert '_scan_and_enqueue("live")' in server
    assert '_scan_and_enqueue("history")' in server
    assert '_enqueue_candidates(' in server
    assert "_merge_history_candidates(all_candidates)" in server
    assert "HISTORY_CHECKS_PER_SCAN = 25" in server
    assert "return join_config.get_source_coil_ids(limit)" in server
    assert "heapq.merge(*id_lists, reverse=True)" in join_config
    assert "DEFAULT_MAX_HISTORY_COIL_COUNT = 500" in main2d
    assert "return range(latest_coil, min_coil - 1, -1)" in main2d
    assert "recovery_coils = join_config.get_source_coil_ids(MAX_HISTORY_COIL_COUNT)" in main2d
    assert "for coil_id in recovery_coils:" in main2d
    assert "142567" not in t_main
    assert "from main2d import main" in t_main
    assert "for surface in self.surfaces.values()" in join_config


def test_2d_join_chain_has_bounded_waits_and_stale_output_guard():
    work_base = (ALGORITHM_2D_ROOT / "JoinService" /
                 "WorkBase.py").read_text(encoding="utf-8")
    join_work = (ALGORITHM_2D_ROOT / "JoinService" /
                 "JoinWork.py").read_text(encoding="utf-8")
    surface_work = (ALGORITHM_2D_ROOT / "JoinService" /
                    "SurfaceWork.py").read_text(encoding="utf-8")
    detection = (ALGORITHM_2D_ROOT / "alg_2d" /
                 "detection.py").read_text(encoding="utf-8")

    assert "self.drain_output()" not in work_base
    assert "class WorkTicket" in work_base
    assert "expected_ticket" in work_base
    assert "deduplicate=True" in join_work
    assert "camera_work.pending_work_ids()" in join_work
    assert "deadline = time.monotonic() + SURFACE_RESULT_TIMEOUT" in join_work
    assert "deadline = time.monotonic() + CAMERA_RESULT_TIMEOUT" in surface_work
    assert "get_source_snapshot" in surface_work
    assert "timeout=AREA_SAVE_QUEUE_TIMEOUT" in surface_work
    assert "persist_detection_results(di, defect_list)" in surface_work
    assert "self._model_lock = Lock()" in detection
    assert "with self._model_lock:" in detection

    server = (ALGORITHM_2D_ROOT / "server.py").read_text(encoding="utf-8")
    coil_check = server[server.index("def _coil_needs_work"):server.index("def _enqueue_candidates")]
    assert coil_check.index("_surface_processed") < coil_check.index("_surface_complete")
