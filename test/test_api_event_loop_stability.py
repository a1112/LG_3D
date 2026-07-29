import asyncio
import json
import sys
import threading
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
for path in (
        PROJECT_ROOT,
        PROJECT_ROOT / "app",
        PROJECT_ROOT / "app" / "Base",
        PROJECT_ROOT / "app" / "Server",
        PROJECT_ROOT / "app" / "algorithm_runtime",
        PROJECT_ROOT / "package" / "CoilDataBase",
):
    path_text = str(path)
    if path_text not in sys.path:
        sys.path.insert(0, path_text)

from api import ApiCompat, ApiDataServer, ApiServer, api_core  # noqa: E402
from fastapi import HTTPException  # noqa: E402


def _exercise_blocked_request(request_factory, entered: threading.Event,
                              release: threading.Event):

    async def exercise():
        blocked_request = asyncio.create_task(request_factory())
        assert await asyncio.to_thread(entered.wait, 1)

        started = time.monotonic()
        health_response = await asyncio.wait_for(api_core.health(), timeout=0.5)
        elapsed = time.monotonic() - started
        release.set()
        response = await blocked_request
        return health_response, response, elapsed

    try:
        return asyncio.run(exercise())
    finally:
        release.set()


def test_software_update_file_probe_does_not_block_health(monkeypatch):
    entered = threading.Event()
    release = threading.Event()

    def blocked_package_probe():
        entered.set()
        release.wait(timeout=2)
        return None

    monkeypatch.setattr(ApiCompat, "_software_update_package_path",
                        blocked_package_probe)

    health_response, manifest, elapsed = _exercise_blocked_request(
        ApiCompat.software_update_manifest, entered, release)

    assert health_response["ok"] is True
    assert manifest["file_name"] == ""
    assert elapsed < 0.5


def test_redetection_database_probe_does_not_block_health(monkeypatch):
    entered = threading.Event()
    release = threading.Event()

    class BlockingRuntime:

        def set_re_detection_by_coil_id(self, from_id, to_id):
            entered.set()
            release.wait(timeout=2)

        def get_re_detection_msg(self):
            return {"ok": True}

    runtime = BlockingRuntime()
    monkeypatch.setattr(ApiServer, "_image_mosaic_thread", lambda: runtime)

    health_response, redetection_response, elapsed = _exercise_blocked_request(
        lambda: ApiServer.http_re_detection_start(1, 2), entered, release)

    assert health_response["ok"] is True
    assert redetection_response == {"ok": True}
    assert elapsed < 0.5


def test_redetection_oversized_range_returns_payload_too_large(monkeypatch):
    class OversizedRuntime:

        def set_re_detection_by_coil_id(self, from_id, to_id):
            raise ValueError("re-detection range exceeds 500 coils")

    monkeypatch.setattr(ApiServer, "_image_mosaic_thread",
                        lambda: OversizedRuntime())

    try:
        asyncio.run(ApiServer.http_re_detection_start(1, 100000))
    except HTTPException as exc:
        assert exc.status_code == 413
        assert "500 coils" in exc.detail
    else:
        raise AssertionError("oversized re-detection range must be rejected")


def test_threadpool_canary_times_out_when_sync_workers_are_unavailable(
        monkeypatch):
    release = threading.Event()

    async def blocked_run_in_threadpool(function):
        await asyncio.to_thread(release.wait, 2)

    monkeypatch.setattr(api_core, "run_in_threadpool",
                        blocked_run_in_threadpool)
    monkeypatch.setattr(api_core, "_THREADPOOL_CANARY_TIMEOUT", 0.05)
    state = {
        "consecutiveFailures": 0,
        "lastSuccessMonotonic": time.monotonic(),
    }

    try:
        asyncio.run(api_core._run_threadpool_canary_probe(state))
    finally:
        release.set()

    assert state["consecutiveFailures"] == 1
    assert state["lastError"] == "TimeoutError"


def test_health_reports_persistently_saturated_threadpool(monkeypatch):
    state = {
        "consecutiveFailures": 3,
        "lastSuccessMonotonic": time.monotonic(),
        "lastProbeDuration": 2.0,
        "lastError": "TimeoutError",
    }
    monkeypatch.setattr(api_core.app.state,
                        "threadpool_canary",
                        state,
                        raising=False)

    response = asyncio.run(api_core.health())

    assert response.status_code == 503
    payload = json.loads(response.body)
    assert payload["ok"] is False
    assert payload["threadpool"]["consecutiveFailures"] == 3


def test_cancelled_height_point_holds_slot_until_worker_finishes(monkeypatch):
    entered = threading.Event()
    release = threading.Event()
    calls = 0

    def blocked_load():
        nonlocal calls
        calls += 1
        entered.set()
        release.wait(timeout=2)
        return calls

    async def exercise():
        semaphore = asyncio.Semaphore(1)
        monkeypatch.setattr(ApiDataServer, "_height_point_slots", semaphore)
        monkeypatch.setattr(ApiDataServer, "_HEIGHT_POINT_ADMISSION_TIMEOUT",
                            0.5)
        monkeypatch.setattr(ApiDataServer, "_HEIGHT_POINT_OPERATION_TIMEOUT",
                            1.0)

        first = asyncio.create_task(
            ApiDataServer._run_height_point_operation(blocked_load))
        assert await asyncio.to_thread(entered.wait, 1)
        first.cancel()
        try:
            await first
        except asyncio.CancelledError:
            pass
        assert semaphore.locked()

        second = asyncio.create_task(
            ApiDataServer._run_height_point_operation(blocked_load))
        await asyncio.sleep(0.05)
        assert not second.done()
        assert calls == 1

        release.set()
        await asyncio.wait_for(second, timeout=1)
        assert calls == 2
        assert not semaphore.locked()

    try:
        asyncio.run(exercise())
    finally:
        release.set()


def test_http_height_point_uses_bounded_worker(monkeypatch):
    observed = []

    class FakeDataGet:

        def __init__(self, *args):
            pass

        def get_3d_data(self):
            observed.append("load")
            return [[7]]

    async def fake_runner(operation):
        observed.append("admit")
        return operation()

    monkeypatch.setattr(ApiDataServer, "DataGet", FakeDataGet)
    monkeypatch.setattr(ApiDataServer, "_run_height_point_operation",
                        fake_runner)

    result = asyncio.run(ApiDataServer.get_height_point("S", "1", 0, 0))

    assert result == 7
    assert observed == ["admit", "load"]


def test_render_health_ignores_transient_full_utilization(monkeypatch):
    monkeypatch.setattr(ApiDataServer, "_RENDER_CONCURRENCY", 2)
    monkeypatch.setattr(ApiDataServer, "_RENDER_HEALTH_STALL_SECONDS", 10.0)
    now = time.monotonic()
    monkeypatch.setattr(ApiDataServer, "_render_operations", {
        1: now,
        2: now,
    })

    health = ApiDataServer._render_executor_health()

    assert health["ok"] is True
    assert health["active"] == 2
    assert health["stalledWorkers"] == 0


def test_health_reports_all_render_workers_stalled(monkeypatch):
    monkeypatch.setattr(ApiDataServer, "_RENDER_CONCURRENCY", 2)
    monkeypatch.setattr(ApiDataServer, "_RENDER_HEALTH_STALL_SECONDS", 1.0)
    now = time.monotonic()
    monkeypatch.setattr(ApiDataServer, "_render_operations", {
        1: now - 5,
        2: now - 5,
    })
    monkeypatch.setattr(api_core.app.state,
                        "render_operation_health",
                        ApiDataServer._render_executor_health,
                        raising=False)

    response = asyncio.run(api_core.health())

    assert response.status_code == 503
    payload = json.loads(response.body)
    assert payload["ok"] is False
    assert payload["renderExecutor"]["stalledWorkers"] == 2
