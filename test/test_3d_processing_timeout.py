import sys
import threading
import time
import importlib
from pathlib import Path
from queue import Queue
from types import SimpleNamespace

import pytest
import torch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = PROJECT_ROOT / "app"
ALGORITHM_ROOT = APP_ROOT / "algorithm_runtime"
BASE_ROOT = APP_ROOT / "Base"
for import_path in (APP_ROOT, BASE_ROOT, ALGORITHM_ROOT):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from Base.alg.CoilClsModel import CoilClsModel
from AlarmDetection.DataProcessing.AlarmLooseCoil import AlarmLooseData
import AlarmDetection.detection as alarm_detection

speed_record_module = importlib.import_module(
    "Base.utils.DetectionSpeedRecord")


class _FakeClassifier(torch.nn.Module):

    def __init__(self):
        super().__init__()
        self.batch_sizes = []

    def forward(self, batch):
        self.batch_sizes.append(batch.shape[0])
        scores = torch.zeros((batch.shape[0], 2), device=batch.device)
        scores[:, 1] = 1
        return scores


def _classifier_for_test():
    classifier = CoilClsModel.__new__(CoilClsModel)
    classifier.device = "cpu"
    classifier.model = _FakeClassifier()
    classifier.names = ["background", "defect"]
    classifier.name_map = {}
    classifier.image_to_tensor = lambda image: torch.as_tensor(
        image, dtype=torch.float32)
    return classifier


def test_classifier_stacks_fixed_size_batches():
    classifier = _classifier_for_test()
    images = [torch.zeros((3, 8, 8)) for _ in range(10)]

    indexes, scores, names = classifier.predict_image(images, bach_size=4)

    assert classifier.model.batch_sizes == [4, 4, 2]
    assert indexes == [1] * 10
    assert names == ["defect"] * 10
    assert len(scores) == 10


def test_classifier_stops_before_work_after_deadline():
    classifier = _classifier_for_test()

    with pytest.raises(TimeoutError, match="classifier preprocessing timeout"):
        classifier.predict_image([torch.zeros((3, 8, 8))],
                                 deadline=time.monotonic() - 1)

    assert classifier.model.batch_sizes == []


def test_runtime_has_bounded_online_stages():
    detection_source = (APP_ROOT / "Base" / "alg" /
                        "detection.py").read_text(encoding="utf-8")
    mosaic_source = (APP_ROOT / "algorithm_runtime" / "SplicingService" /
                     "ImageMosaic.py").read_text(encoding="utf-8")
    thread_source = (APP_ROOT / "algorithm_runtime" / "SplicingService" /
                     "ImageMosaicThread.py").read_text(encoding="utf-8")
    storage_source = (APP_ROOT / "Base" / "tools" /
                      "compressed_storage.py").read_text(encoding="utf-8")
    control_source = (APP_ROOT / "Base" / "utils" /
                      "ControlManagement.py").read_text(encoding="utf-8")

    assert "LG3D_DETECTION_TIMEOUT_SECONDS" in detection_source
    assert "LG3D_CLASSIFIER_TIMEOUT_SECONDS" in detection_source
    assert "LG3D_MAX_CLASSIFIER_CANDIDATES" in detection_source
    assert "LG3D_MAX_CLASSIFIER_SAVED_IMAGES" in detection_source
    assert '_check_deadline(deadline, "classifier image saving")' in detection_source
    assert "DEFAULT_MOSAIC_RESULT_TIMEOUT = 60.0" in mosaic_source
    assert "LG3D_COIL_PROCESSING_TIMEOUT_SECONDS" in thread_source
    assert "alarm detection skipped: coil processing timeout" in thread_source
    assert "compress_level=1, optimize=False" in storage_source
    assert "self.ImageSaverWorkNum = 4" in control_source
    assert "self.ImageSaverQueueSize = 16" in control_source
    assert "DEFAULT_MAX_HISTORY_COIL_COUNT = 10" in thread_source
    assert "ALGORITHM_3D_REPROCESS_MISSING_OUTPUTS" in thread_source
    assert "if not REPROCESS_MISSING_OUTPUTS:" in thread_source


def test_mosaic_coordinator_stop_is_nonblocking_and_propagates():
    from SplicingService.ImageMosaicThread import ImageMosaicThread

    class FakeMosaic:
        key = "S"

        def __init__(self):
            self.stop_requested = False

        def request_stop(self):
            self.stop_requested = True

    coordinator = ImageMosaicThread.__new__(ImageMosaicThread)
    threading.Thread.__init__(coordinator, daemon=True)
    coordinator._stop_event = threading.Event()
    child = FakeMosaic()
    coordinator.imageMosaicList = [child]

    coordinator.stop()

    assert coordinator._stop_event.is_set()
    assert child.stop_requested
    assert coordinator.daemon


def test_re_detection_queue_rejects_oversized_ranges_and_bounds_status(
        monkeypatch):
    thread_module = importlib.import_module(
        "SplicingService.ImageMosaicThread")
    coordinator = thread_module.ImageMosaicThread.__new__(
        thread_module.ImageMosaicThread)
    coordinator.re_detection_queue = [99]
    coordinator.re_detection_total = 1
    coordinator.re_detection_done = 0
    coordinator.re_detection_running = False
    coordinator.re_detection_error = ""
    coordinator.re_detection_messages = []
    coordinator.add_msg = lambda *args, **kwargs: None
    monkeypatch.setattr(thread_module, "MAX_RE_DETECTION_COIL_COUNT", 2)

    def oversized_query(start_id, end_id, max_count=None):
        assert (start_id, end_id, max_count) == (1, 1000, 2)
        raise thread_module.Coil.QueryResultLimitExceeded(max_count)

    monkeypatch.setattr(thread_module.Coil,
                        "get_secondary_coil_ids_by_range", oversized_query)

    with pytest.raises(ValueError, match="2 records"):
        coordinator.set_re_detection_by_coil_id(1, 1000)
    assert coordinator.re_detection_queue == [99]

    coordinator.re_detection_queue = [3, 2, 1]
    status = coordinator.get_re_detection_msg()
    assert status["queue"] == [3, 2]
    assert status["queue_size"] == 3
    assert status["queue_truncated"] is True

    coordinator.re_detection_queue = [3, 2]
    with pytest.raises(ValueError, match="2 coils"):
        coordinator.set_re_detection(1)


def test_data_folder_result_queue_replaces_stale_result(monkeypatch):
    from SplicingService import DataFolder as data_folder_module

    worker = data_folder_module.DataFolder.__new__(data_folder_module.DataFolder)
    worker.consumer = Queue(maxsize=1)
    worker.folderName = "Cap_S_U"
    worker._stop_event = threading.Event()
    monkeypatch.setattr(data_folder_module, "DATA_FOLDER_QUEUE_TIMEOUT", 0.01)
    worker.consumer.put_nowait({"coil_id": "old"})

    worker._publish_result({"coil_id": "new"})

    assert worker.get_data(timeout=0.1, expected_coil_id="new") == {"coil_id": "new"}


def test_loose_coil_uses_only_common_rotations():
    surface_s = SimpleNamespace(coilId=1001, surface="S")
    surface_l = SimpleNamespace(coilId=1001, surface="L")
    s_60 = object()
    s_90 = object()
    l_90 = object()
    l_170 = object()

    loose_data = AlarmLooseData([
        [surface_s, {
            60: s_60,
            90: s_90
        }],
        [surface_l, {
            90: l_90,
            170: l_170
        }],
    ])

    assert loose_data.lineDataDicts == {90: [s_90, l_90]}


def test_alarm_stage_failure_does_not_skip_following_stages(monkeypatch):
    calls = []

    def stage(label, fail=False):

        def run(_):
            calls.append(label)
            if fail:
                raise KeyError(label)

        return run

    monkeypatch.setattr(alarm_detection, "_detectionAlarmFlatRollAll_",
                        stage("flat"))
    monkeypatch.setattr(alarm_detection, "_detection_taper_shape_all_",
                        stage("taper"))
    monkeypatch.setattr(alarm_detection, "_detectionAlarmLooseCoilAll_",
                        stage("loose", fail=True))
    monkeypatch.setattr(alarm_detection, "_detectionAlarmDefectAll_",
                        stage("defect"))
    monkeypatch.setattr(alarm_detection, "grading_all", stage("grading"))

    alarm_detection.detection_all([SimpleNamespace(coilId=1001)])

    assert calls == ["flat", "taper", "loose", "defect", "grading"]


def test_normal_stitch_duration_is_warning_not_error(monkeypatch):
    messages = []
    ticks = iter((10.0, 20.0))
    monkeypatch.setattr(speed_record_module.time, "perf_counter",
                        lambda: next(ticks))
    monkeypatch.setattr(speed_record_module.logger, "info",
                        lambda *args: messages.append("info"))
    monkeypatch.setattr(speed_record_module.logger, "warning",
                        lambda *args: messages.append("warning"))
    monkeypatch.setattr(speed_record_module.logger, "error",
                        lambda *args: messages.append("error"))

    @speed_record_module.DetectionSpeedRecord.timing_decorator("stitch")
    def work():
        return "ok"

    assert work() == "ok"
    assert messages == ["warning"]
