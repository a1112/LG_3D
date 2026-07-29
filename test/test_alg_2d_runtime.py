import logging
import sys
import time
from collections import deque
from pathlib import Path
from queue import Queue
from threading import Event, Lock, Thread
from types import SimpleNamespace

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = PROJECT_ROOT / "app"
ALG_2D_ROOT = PROJECT_ROOT / "app" / "algorithm_runtime_2D"
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))
if str(ALG_2D_ROOT) not in sys.path:
    sys.path.insert(0, str(ALG_2D_ROOT))


class RunningConfig:
    def is_run(self):
        return True


def test_base_config_closes_json_file(tmp_path):
    from algorithm_runtime_2D.configs.BaseConfig import BaseConfig

    config_path = tmp_path / "config.json"
    config_path.write_text('{"enabled": true}', encoding="utf-8")

    config = BaseConfig(config_path)

    assert config.get_value("enabled", False) is True
    # Windows refuses this replace when the configuration file is still open.
    replacement = tmp_path / "replacement.json"
    replacement.write_text("{}", encoding="utf-8")
    replacement.replace(config_path)


def test_recovery_queue_merges_full_new_burst_beyond_live_window():
    from algorithm_runtime_2D.JoinService.RecoveryQueue import merge_history_candidates

    history = deque([105, 104, 103, 102, 101])
    known_ids = set(history)
    source_ids = list(range(112, 100, -1))

    discovered = merge_history_candidates(history, known_ids, source_ids)

    assert discovered == [112, 111, 110, 109, 108, 107, 106]
    assert list(history)[:7] == discovered


def test_recovery_queue_and_known_ids_stay_bounded_across_moving_windows():
    from algorithm_runtime_2D.JoinService.RecoveryQueue import merge_history_candidates

    history = deque()
    known_ids = set()
    for newest in range(100, 1100, 100):
        source_ids = list(range(newest, newest - 100, -1))
        merge_history_candidates(history,
                                 known_ids,
                                 source_ids,
                                 max_candidates=125)

    assert len(history) == 125
    assert len(known_ids) == 125
    assert known_ids == set(history)
    assert history[0] == 1000


def test_recovery_retry_state_prunes_evicted_coils():
    from algorithm_runtime_2D.JoinService.RecoveryQueue import prune_retry_state

    retry_state = {
        coil_id: {
            "attempts": 1
        }
        for coil_id in range(20)
    }
    retained_ids = set(range(10, 20))

    prune_retry_state(retry_state, retained_ids, max_entries=6)

    assert len(retry_state) == 6
    assert set(retry_state).issubset(retained_ids)


def test_2d_main_logger_only_uses_nonblocking_queue_handler():
    from algorithm_runtime_2D.utils import MultiprocessColorLogger as logger_module

    assert len(logger_module.logger.handlers) == 1
    assert isinstance(
        logger_module.logger.handlers[0],
        logger_module.DroppingQueueHandler,
    )


def test_manual_rejoin_uses_fixed_result_consumers_instead_of_per_request_threads():
    source = (ALG_2D_ROOT / "server.py").read_text(encoding="utf-8")
    endpoint_source = source.split("def rejoin_area", 1)[1].split(
        "@app.get(\"/area/status\")", 1)[0]

    assert "manual_result_executors[key].submit" in endpoint_source
    assert "Thread(" not in endpoint_source
    assert "executor.shutdown(wait=False, cancel_futures=True)" in source


def test_2d_queue_handler_drops_records_immediately_when_full():
    from algorithm_runtime_2D.utils.MultiprocessColorLogger import DroppingQueueHandler

    for level in (logging.INFO, logging.ERROR):
        queue = Queue(maxsize=1)
        queue.put_nowait(object())
        handler = DroppingQueueHandler(queue)
        record = logging.LogRecord("test", level, __file__, 1, "message", (), None)

        started = time.monotonic()
        handler.emit(record)

        assert time.monotonic() - started < 0.05


def test_recovery_queue_limits_incomplete_checks_and_rotates_backlog():
    from algorithm_runtime_2D.JoinService.RecoveryQueue import take_next_history_candidate

    history = deque(range(1, 31))
    checked = []

    def evaluate(coil_id):
        checked.append(coil_id)
        return False, "incomplete"

    result = take_next_history_candidate(
        history,
        evaluate,
        max_checks=25,
    )

    assert result is None
    assert checked == list(range(1, 26))
    assert history[0] == 26


def test_work_queue_deduplicates_queued_and_active_items():
    from algorithm_runtime_2D.JoinService.WorkBase import WorkBaseThread

    worker = WorkBaseThread(RunningConfig(), deduplicate=True)
    ticket = worker.add_work(101, timeout=0)

    assert ticket is not None
    assert worker.add_work(101, timeout=0) is None
    request = worker.queue_in.get_nowait()
    worker.mark_started(request)
    assert worker.has_pending(101)
    assert worker.add_work(101, timeout=0) is None

    worker.set("done", work_request=request)
    worker.mark_finished(request)
    worker.queue_in.task_done()

    assert worker.get(timeout=0.1, expected_ticket=ticket) == "done"
    assert not worker.has_pending(101)


def test_work_queue_rolls_back_full_queue_reservation():
    from algorithm_runtime_2D.JoinService.WorkBase import WorkBaseThread

    worker = WorkBaseThread(RunningConfig(), deduplicate=True)
    worker.queue_in = Queue(maxsize=1)
    first_ticket = worker.add_work(1, timeout=0)

    assert first_ticket is not None
    assert worker.add_work(2, timeout=0) is None
    assert 2 not in worker.pending_work_ids()

    first_request = worker.queue_in.get_nowait()
    worker.mark_started(first_request)
    worker.mark_finished(first_request)
    worker.queue_in.task_done()

    assert worker.add_work(2, timeout=0) is not None


def test_work_results_use_submission_ticket_for_same_coil_retry():
    from algorithm_runtime_2D.JoinService.WorkBase import WorkBaseThread

    worker = WorkBaseThread(RunningConfig(), deduplicate=True)
    first_ticket = worker.add_work(7, timeout=0)
    first_request = worker.queue_in.get_nowait()
    worker.mark_started(first_request)
    worker.set("old", work_request=first_request)
    worker.mark_finished(first_request)
    worker.queue_in.task_done()

    second_ticket = worker.add_work(7, timeout=0)
    second_request = worker.queue_in.get_nowait()
    worker.mark_started(second_request)
    worker.set("new", work_request=second_request)
    worker.mark_finished(second_request)
    worker.queue_in.task_done()

    assert first_ticket != second_ticket
    assert worker.get(timeout=0.1, expected_ticket=second_ticket) == "new"
    assert worker.get(timeout=0.1, expected_ticket=first_ticket) == "old"


def test_work_result_timeout_zero_still_consumes_already_queued_result():
    from algorithm_runtime_2D.JoinService.WorkBase import WorkBaseThread

    worker = WorkBaseThread(RunningConfig())
    ticket = worker.add_work(8, timeout=0)
    request = worker.queue_in.get_nowait()
    worker.mark_started(request)
    worker.set("ready", work_request=request)
    worker.mark_finished(request)

    assert worker.get(timeout=0, expected_ticket=ticket) == "ready"


def test_late_result_is_discarded_after_ticket_timeout():
    from algorithm_runtime_2D.JoinService.WorkBase import WorkBaseThread

    worker = WorkBaseThread(RunningConfig())
    ticket = worker.add_work(9, timeout=0)
    request = worker.queue_in.get_nowait()
    worker.mark_started(request)

    assert worker.get(timeout=0, expected_ticket=ticket) is None
    assert worker.set("late", work_request=request)
    assert worker.queue_out.empty()


def test_idle_work_thread_stops_without_permanent_queue_get():
    from algorithm_runtime_2D.JoinService.WorkBase import WorkBaseThread

    class IdleWorker(WorkBaseThread):
        def run(self):
            while True:
                request = self.get_next_work(poll_timeout=0.01)
                if request is None:
                    return

    worker = IdleWorker(RunningConfig())
    worker.start()

    assert worker.stop(timeout=1)
    assert not worker.is_alive()
    assert worker.add_work(1, timeout=0) is None


def test_disabled_saver_remains_available_until_explicit_stop():
    from algorithm_runtime_2D.JoinService.SaverWork import SaverWork

    class DisabledConfig:
        @staticmethod
        def is_run():
            return False

    saver = SaverWork(DisabledConfig())
    try:
        time.sleep(0.05)
        assert saver.is_alive()
    finally:
        assert saver.stop(timeout=1)


def test_uncorrelated_timeout_does_not_abandon_pending_ticket():
    from algorithm_runtime_2D.JoinService.WorkBase import WorkBaseThread

    worker = WorkBaseThread(RunningConfig())
    ticket = worker.add_work(10, timeout=0)
    request = worker.queue_in.get_nowait()
    worker.mark_started(request)

    assert worker.get(timeout=0) is None
    assert worker.set("ready", work_request=request)
    assert worker.get(timeout=0, expected_ticket=ticket) == "ready"


def test_concurrent_work_result_waiters_do_not_steal_each_others_results():
    from algorithm_runtime_2D.JoinService.WorkBase import WorkBaseThread

    worker = WorkBaseThread(RunningConfig())
    first_ticket = worker.add_work(1, timeout=0)
    second_ticket = worker.add_work(2, timeout=0)
    first_request = worker.queue_in.get_nowait()
    second_request = worker.queue_in.get_nowait()
    results = {}

    first_waiter = Thread(
        target=lambda: results.setdefault("first", worker.get(timeout=1, expected_ticket=first_ticket))
    )
    second_waiter = Thread(
        target=lambda: results.setdefault("second", worker.get(timeout=1, expected_ticket=second_ticket))
    )
    first_waiter.start()
    second_waiter.start()
    time.sleep(0.05)
    worker.set("second", work_request=second_request)
    worker.set("first", work_request=first_request)
    first_waiter.join(timeout=1)
    second_waiter.join(timeout=1)

    assert results == {"first": "first", "second": "second"}


def _source_snapshot(*, latest_mtime_ns: int, missing_middle: bool = False, zero_size: bool = False):
    snapshot = []
    for camera_index, camera_key in enumerate(("U", "M", "D")):
        files = () if missing_middle and camera_key == "M" else (
            ("1.jpg", 0 if zero_size and camera_index == 0 else 10, latest_mtime_ns),
            ("2.jpg", 10, latest_mtime_ns),
        )
        snapshot.append((camera_key, files))
    return tuple(snapshot)


def test_source_snapshot_requires_complete_quiet_nonempty_inputs():
    from algorithm_runtime_2D.configs.SurfaceConfig import SurfaceConfig

    old_mtime_ns = time.time_ns() - 20_000_000_000
    ready = _source_snapshot(latest_mtime_ns=old_mtime_ns)

    assert SurfaceConfig.source_snapshot_complete(ready, quiet_seconds=10)
    assert not SurfaceConfig.source_snapshot_complete(
        _source_snapshot(latest_mtime_ns=old_mtime_ns, missing_middle=True),
        quiet_seconds=10,
    )
    assert not SurfaceConfig.source_snapshot_complete(
        _source_snapshot(latest_mtime_ns=old_mtime_ns, zero_size=True),
        quiet_seconds=10,
    )
    assert not SurfaceConfig.source_snapshot_complete(
        _source_snapshot(latest_mtime_ns=time.time_ns()),
        quiet_seconds=10,
    )


def test_surface_completion_marker_distinguishes_legacy_and_partial_outputs(monkeypatch, tmp_path):
    from algorithm_runtime_2D.configs import SurfaceConfig as surface_config_module

    monkeypatch.setattr(surface_config_module.CONFIG, "DEBUG", False)
    config = surface_config_module.SurfaceConfig.__new__(surface_config_module.SurfaceConfig)
    config.save_folder = tmp_path
    area_path = config.get_area_url(10)
    area_path.parent.mkdir(parents=True)
    area_path.write_bytes(b"legacy")

    assert config.area_output_complete(10)
    config.get_area_in_progress_marker(10).write_text("saving", encoding="utf-8")
    assert not config.area_output_complete(10)
    config.get_area_completion_marker(10).write_text("complete", encoding="utf-8")
    assert config.area_output_complete(10)
    area_path.unlink()
    assert not config.area_output_complete(10)


def test_camera_group_normalizes_missing_mask_without_full_size_allocation(monkeypatch):
    from app.algorithm_runtime_2D.property import CameraImageGrop as camera_group_module

    monkeypatch.setattr(camera_group_module.CONFIG, "DEBUG", False)
    monkeypatch.setattr(camera_group_module, "DEBUG", False)

    class DummyResult:
        def __init__(self, image, mask):
            self.image = image
            self._mask = mask
            self.result = object()

        def get_mask(self):
            return self._mask

    surface_config = SimpleNamespace(image_size=40, scale=10)
    config = SimpleNamespace(key="Cap_L_U", surface_key="L", surface_config=surface_config)
    image = np.zeros((40, 40, 3), dtype=np.uint8)
    results = [
        DummyResult(image, np.full((4, 4), 255, dtype=np.uint8)),
        DummyResult(image, None),
    ]

    group = camera_group_module.CameraImageGrop(1, config, results)
    joined_mask = group.join_mask()

    assert [mask.shape for mask in group.mask_list] == [(4, 4), (4, 4)]
    assert all(mask.dtype == np.uint8 for mask in group.mask_list)
    assert group.mask_list[1].nbytes == 16
    assert joined_mask.shape == (4, 8)


def test_camera_group_fits_shared_intersections_to_local_frame_count(monkeypatch):
    from app.algorithm_runtime_2D.property import CameraImageGrop as camera_group_module

    monkeypatch.setattr(camera_group_module.CONFIG, "DEBUG", False)
    monkeypatch.setattr(camera_group_module, "DEBUG", False)

    class DummyResult:
        def __init__(self):
            self.image = np.zeros((40, 40, 3), dtype=np.uint8)
            self.result = object()

        @staticmethod
        def get_mask():
            return np.full((4, 4), 255, dtype=np.uint8)

    surface_config = SimpleNamespace(image_size=40, scale=10)
    config = SimpleNamespace(key="Cap_L_M", surface_key="L", surface_config=surface_config)
    group = camera_group_module.CameraImageGrop(1, config, [DummyResult(), DummyResult()])

    group.set_stitching(0, 2, [10, 10])
    group.init_image()

    assert len(group.image_list) == 2
    assert len(group.intersections) == 1
    assert len(group.mask_intersections) == 1
    assert group.join_image().shape == (40, 50, 3)

    group.release()

    assert group.image_list == []
    assert group.mask_list == []
    assert group.results is None


def test_surface_intersections_do_not_median_misaligned_camera_frames():
    from algorithm_runtime_2D.JoinService.SurfaceWork import SurfaceWork

    upper = SimpleNamespace(
        left_index=0,
        right_index=3,
        intersections=[2510, 2320, 2330, 2370, 0],
    )
    middle = SimpleNamespace(
        left_index=0,
        right_index=3,
        intersections=[4370, 0, 2430, 2340, 0],
    )
    lower = SimpleNamespace(
        left_index=0,
        right_index=2,
        intersections=[0, 2500, 2470, 0],
    )
    surface = SurfaceWork.__new__(SurfaceWork)

    intersections, left_index, right_index = surface.get_intersections(
        [upper, middle, lower])

    assert intersections == [2510, 2320, 2330, 2340, 0]
    assert (left_index, right_index) == (0, 3)


def test_surface_pipeline_serializes_large_surface_lifecycles():
    source = (ALG_2D_ROOT / "JoinService" / "SurfaceWork.py").read_text(
        encoding="utf-8")

    assert '_int_env("ALG_2D_SURFACE_PIPELINE_CONCURRENCY", 1, 1)' in source
    assert "SURFACE_PIPELINE_SEMAPHORE.acquire()" in source
    assert "SURFACE_PIPELINE_SEMAPHORE.release()" in source
    assert "self.save_wolk.wait_for_completion(" in source
    assert "release_inference_caches()" in source


def test_release_inference_caches_collects_python_and_cuda(monkeypatch):
    from algorithm_runtime_2D.utils import model_memory

    calls = []
    fake_cuda = SimpleNamespace(
        is_available=lambda: True,
        empty_cache=lambda: calls.append("cuda"),
    )
    monkeypatch.setattr(model_memory.gc, "collect",
                        lambda: calls.append("gc"))
    monkeypatch.setitem(sys.modules, "torch", SimpleNamespace(cuda=fake_cuda))

    model_memory.release_inference_caches()

    assert calls == ["gc", "cuda"]


def test_segmentation_predict_honors_explicit_batch_size(monkeypatch):
    from algorithm_runtime_2D.area_alg import YoloSeg as yolo_seg_module

    calls = []

    class FakeModel:
        def __init__(self):
            self.predictor = SimpleNamespace(
                dataset=None,
                batch=None,
                results=None,
                plotted_img=None,
            )

        def __call__(self, batch, *, verbose):
            calls.append(len(batch))
            results = list(range(len(batch)))
            self.predictor.dataset = SimpleNamespace(im0=batch)
            self.predictor.batch = ([], batch, [])
            self.predictor.results = results
            self.predictor.plotted_img = batch[-1]
            return results

    monkeypatch.setattr(
        yolo_seg_module,
        "YoloModelSegResults",
        lambda image, result: (image, result),
    )
    model = yolo_seg_module.SteelSegModel.__new__(yolo_seg_module.SteelSegModel)
    model.model = FakeModel()
    model._model_lock = Lock()

    output = model.predict(list(range(10)), batch_size=4)
    single = model.predict_one(99)

    assert calls == [4, 4, 2, 1]
    assert [image for image, _ in output] == list(range(10))
    assert single == (99, 0)
    assert model.model.predictor.dataset is None
    assert model.model.predictor.batch is None
    assert model.model.predictor.results is None
    assert model.model.predictor.plotted_img is None


def test_segmentation_result_releases_ultralytics_original_image():
    from algorithm_runtime_2D.area_alg.YoloModelResults import YoloModelResultsBase

    result = SimpleNamespace(orig_img=np.ones((4, 4, 3), dtype=np.uint8), names={}, boxes=[])
    wrapped = YoloModelResultsBase(np.zeros((4, 4, 3), dtype=np.uint8), result)

    assert wrapped.result.orig_img is None


def test_classifier_serializes_shared_model_prediction(monkeypatch):
    from algorithm_runtime_2D.alg_2d import classifier

    state_lock = Lock()
    active_calls = 0
    max_active_calls = 0

    class FakeClassifier:
        @staticmethod
        def predict_image(images):
            nonlocal active_calls, max_active_calls
            with state_lock:
                active_calls += 1
                max_active_calls = max(max_active_calls, active_calls)
            time.sleep(0.05)
            with state_lock:
                active_calls -= 1
            count = len(images)
            return [1] * count, [0.9] * count, ["ok"] * count

    monkeypatch.setattr(classifier.CONFIG, "enable_classifier", True)
    monkeypatch.setattr(classifier, "_classifier_load_failed", False)
    monkeypatch.setattr(classifier, "_classifier_model", FakeClassifier())
    source = np.zeros((32, 32, 3), dtype=np.uint8)
    outputs = []

    threads = [
        Thread(target=lambda: outputs.append(classifier.classify_boxes(source, [(1, 1, 10, 10)])))
        for _ in range(2)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=1)

    assert max_active_calls == 1
    assert len(outputs) == 2


def test_saver_keeps_coil_pending_until_all_outputs_finish(monkeypatch, tmp_path):
    from algorithm_runtime_2D.JoinService.SaverWork import SaverWork

    class SaveConfig(RunningConfig):
        def get_area_url(self, coil_id, name="AREA"):
            return tmp_path / str(coil_id) / "jpg" / f"{name}.jpg"

        def get_area_url_pre(self, coil_id, name="AREA"):
            return tmp_path / str(coil_id) / "preview" / f"{name}.jpg"

    started = Event()
    release = Event()
    original_write_tiles = SaverWork._write_tile_cache

    def blocking_write_tiles(self, area_path, image):
        started.set()
        assert release.wait(2)
        return original_write_tiles(self, area_path, image)

    monkeypatch.setattr(SaverWork, "_write_tile_cache", blocking_write_tiles)
    saver = SaverWork(SaveConfig())
    image = np.zeros((9, 9, 3), dtype=np.uint8)
    mask = np.ones((9, 9), dtype=np.uint8) * 255
    ticket = saver.add_work([123, image, mask], timeout=0)

    assert ticket is not None
    assert started.wait(1)
    assert saver.has_pending(123)
    release.set()

    deadline = time.monotonic() + 5
    while saver.has_pending(123) and time.monotonic() < deadline:
        time.sleep(0.01)

    assert not saver.has_pending(123)
    assert (tmp_path / "123" / "jpg" / "AREA.jpg").exists()
    assert (tmp_path / "123" / "jpg" / "AREA_MASK.jpg").exists()
    assert (tmp_path / "123" / "preview" / "AREA.jpg").exists()
    assert (tmp_path / "123" / "cache" / "area" / "tild" / "L4" / "0_0.jpg").exists()
    assert (tmp_path / "123" / "cache" / "area" / "AREA_MASK" / "tild" / "L4" / "0_0.jpg").exists()
    assert (tmp_path / "123" / ".area_complete").exists()
    assert not (tmp_path / "123" / ".area_in_progress").exists()


def test_saver_leaves_partial_marker_when_post_area_save_fails(monkeypatch, tmp_path):
    from algorithm_runtime_2D.JoinService.SaverWork import SaverWork

    class SaveConfig(RunningConfig):
        def get_area_url(self, coil_id, name="AREA"):
            return tmp_path / str(coil_id) / "jpg" / f"{name}.jpg"

        def get_area_url_pre(self, coil_id, name="AREA"):
            return tmp_path / str(coil_id) / "preview" / f"{name}.jpg"

    def fail_tiles(*_args, **_kwargs):
        raise OSError("simulated tile failure")

    monkeypatch.setattr(SaverWork, "_write_tile_cache", fail_tiles)
    saver = SaverWork(SaveConfig())
    assert saver.add_work([321, np.zeros((9, 9, 3), dtype=np.uint8), None], timeout=0)

    deadline = time.monotonic() + 5
    while saver.has_pending(321) and time.monotonic() < deadline:
        time.sleep(0.01)

    assert not saver.has_pending(321)
    assert (tmp_path / "321" / "jpg" / "AREA.jpg").exists()
    assert (tmp_path / "321" / ".area_in_progress").exists()
    assert not (tmp_path / "321" / ".area_complete").exists()
