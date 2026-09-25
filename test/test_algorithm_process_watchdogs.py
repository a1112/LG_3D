import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = PROJECT_ROOT / "app"
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))
RUNTIMES = {
    "3d": {
        "folder": APP_ROOT / "algorithm_runtime",
        "service": "LG3D_ALGORITHM_3D",
    },
    "2d": {
        "folder": APP_ROOT / "algorithm_runtime_2D",
        "service": "LG3D_ALGORITHM_2D",
    },
}


def _load_module(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("runtime_key", ["3d", "2d"])
def test_watchdog_accepts_only_fresh_matching_heartbeat(runtime_key, tmp_path):
    runtime = RUNTIMES[runtime_key]
    watchdog = _load_module(
        runtime["folder"] / "watchdog.py",
        f"algorithm_{runtime_key}_watchdog_test_fresh",
    )
    heartbeat_path = tmp_path / f"{runtime_key}.json"
    process = SimpleNamespace(pid=321)
    heartbeat_path.write_text(
        json.dumps(
            {
                "service": runtime["service"],
                "pid": process.pid,
                "updatedAtEpoch": 100.0,
                "status": "ok",
                "activities": [],
            }
        ),
        encoding="utf-8",
    )

    healthy, reason = watchdog.heartbeat_health(
        process,
        path=heartbeat_path,
        now=100.0,
    )

    assert healthy is True
    assert reason == "ok"

    wrong_process, reason = watchdog.heartbeat_health(
        SimpleNamespace(pid=999),
        path=heartbeat_path,
        now=100.0,
    )
    assert wrong_process is False
    assert reason == "heartbeat_pid_mismatch"

    stale, reason = watchdog.heartbeat_health(
        process,
        path=heartbeat_path,
        now=100.0 + watchdog.HEARTBEAT_TIMEOUT + 1,
    )
    assert stale is False
    assert reason.startswith("heartbeat_stale:")


@pytest.mark.parametrize("runtime_key", ["3d", "2d"])
def test_watchdog_rejects_overdue_native_activity(runtime_key, tmp_path):
    runtime = RUNTIMES[runtime_key]
    watchdog = _load_module(
        runtime["folder"] / "watchdog.py",
        f"algorithm_{runtime_key}_watchdog_test_overdue",
    )
    heartbeat_path = tmp_path / f"{runtime_key}.json"
    process = SimpleNamespace(pid=654)
    heartbeat_path.write_text(
        json.dumps(
            {
                "service": runtime["service"],
                "pid": process.pid,
                "updatedAtEpoch": 200.0,
                "status": "ok",
                "activities": [
                    {
                        "name": "native_inference",
                        "workId": "coil-10",
                        "deadlineAtEpoch": 199.0,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    healthy, reason = watchdog.heartbeat_health(
        process,
        path=heartbeat_path,
        now=200.0,
    )

    assert healthy is False
    assert reason == "activity_overdue:native_inference:coil-10"


@pytest.mark.parametrize("runtime_key", ["3d", "2d"])
def test_watchdog_restart_backoff_is_exponential_and_capped(runtime_key, monkeypatch):
    runtime = RUNTIMES[runtime_key]
    watchdog = _load_module(
        runtime["folder"] / "watchdog.py",
        f"algorithm_{runtime_key}_watchdog_test_backoff",
    )
    monkeypatch.setattr(watchdog, "RESTART_DELAY", 5.0)
    monkeypatch.setattr(watchdog, "RESTART_MAX_DELAY", 20.0)

    assert watchdog.restart_backoff_seconds(1) == 5.0
    assert watchdog.restart_backoff_seconds(2) == 10.0
    assert watchdog.restart_backoff_seconds(3) == 20.0
    assert watchdog.restart_backoff_seconds(20) == 20.0


@pytest.mark.parametrize("runtime_key", ["3d", "2d"])
def test_watchdog_honors_startup_grace_and_consecutive_failure_threshold(
    runtime_key,
    monkeypatch,
):
    runtime = RUNTIMES[runtime_key]
    watchdog = _load_module(
        runtime["folder"] / "watchdog.py",
        f"algorithm_{runtime_key}_watchdog_test_threshold",
    )

    class FakeProcess:
        pid = 987

        def poll(self):
            return None

    clock = {"value": 0.0}
    stopped = []
    health_calls = []

    def fake_sleep(seconds):
        clock["value"] += seconds
        if stopped:
            raise KeyboardInterrupt

    monkeypatch.setattr(watchdog, "start_algorithm_process", FakeProcess)
    monkeypatch.setattr(watchdog, "stop_algorithm_process", lambda process: stopped.append(process.pid))
    monkeypatch.setattr(
        watchdog,
        "heartbeat_health",
        lambda process: (health_calls.append(process.pid) or False, "stalled"),
    )
    monkeypatch.setattr(watchdog.time, "monotonic", lambda: clock["value"])
    monkeypatch.setattr(watchdog.time, "sleep", fake_sleep)
    monkeypatch.setattr(watchdog, "CHECK_INTERVAL", 5.0)
    monkeypatch.setattr(watchdog, "STARTUP_GRACE", 10.0)
    monkeypatch.setattr(watchdog, "FAILURE_THRESHOLD", 2)

    watchdog.supervise_algorithm_process()

    assert health_calls == [987, 987]
    assert stopped == [987]


@pytest.mark.parametrize("runtime_key", ["3d", "2d"])
def test_runtime_heartbeat_atomically_reports_activity_timeout(runtime_key, tmp_path):
    runtime = RUNTIMES[runtime_key]
    heartbeat_module = _load_module(
        runtime["folder"] / "runtime_heartbeat.py",
        f"algorithm_{runtime_key}_heartbeat_test",
    )
    heartbeat = heartbeat_module.RuntimeHeartbeat()
    heartbeat.path = tmp_path / f"heartbeat-{runtime_key}.json"
    token = heartbeat.begin_activity(
        "native_inference",
        42,
        timeout_seconds=10,
    )
    activity = heartbeat._activities[token]

    assert heartbeat.write_once(now=activity["deadlineAtEpoch"] + 1)
    payload = json.loads(heartbeat.path.read_text(encoding="utf-8"))
    assert payload["status"] == "stalled"
    assert payload["overdueActivities"][0]["workId"] == "42"
    assert not list(tmp_path.glob("*.tmp"))

    heartbeat.end_activity(token)
    assert heartbeat.write_once(now=activity["deadlineAtEpoch"] + 2)
    payload = json.loads(heartbeat.path.read_text(encoding="utf-8"))
    assert payload["status"] == "ok"
    assert payload["activities"] == []


def test_algorithm_entrypoints_keep_required_supervision_hooks():
    main_3d = (RUNTIMES["3d"]["folder"] / "main.py").read_text(encoding="utf-8")
    mosaic_thread = (
        RUNTIMES["3d"]["folder"]
        / "SplicingService"
        / "ImageMosaicThread.py"
    ).read_text(encoding="utf-8")
    server_2d = (RUNTIMES["2d"]["folder"] / "server.py").read_text(encoding="utf-8")
    work_base_2d = (
        RUNTIMES["2d"]["folder"] / "JoinService" / "WorkBase.py"
    ).read_text(encoding="utf-8")

    assert 'os.getenv("LG3D_ENABLE_LEGACY_CAPTURE_LIS", "0") == "1"' in main_3d
    assert "runtime_heartbeat.start()" in main_3d
    assert "_process_secondary_coil_supervised" in mosaic_thread
    assert '@app.get("/health")' in server_2d
    assert "runtime_heartbeat.begin_activity" in work_base_2d
    assert "runtime_heartbeat.end_activity" in work_base_2d


def test_2d_worker_activity_remains_registered_until_state_cleanup():
    from algorithm_runtime_2D.JoinService.WorkBase import WorkBaseThread
    from algorithm_runtime_2D.runtime_heartbeat import runtime_heartbeat

    class RunningConfig:
        @staticmethod
        def is_run():
            return True

    worker = WorkBaseThread(RunningConfig())
    ticket = worker.add_work(77, timeout=0)
    request = worker.queue_in.get_nowait()
    before = len(runtime_heartbeat._activities)

    worker.mark_started(request)

    assert len(runtime_heartbeat._activities) == before + 1
    activity = runtime_heartbeat._activities[worker._heartbeat_activity_token]
    assert activity["name"] == "WorkBaseThread"
    assert activity["workId"] == "77"

    worker.mark_finished(request)
    assert ticket is not None
    assert len(runtime_heartbeat._activities) == before


@pytest.mark.parametrize("runtime_key", ["3d", "2d"])
def test_watchdog_start_script_uses_python_311_and_async_logging(runtime_key):
    runtime_folder = RUNTIMES[runtime_key]["folder"]
    start_script = (runtime_folder / "start_watchdog.bat").read_text(
        encoding="utf-8"
    )
    watchdog_source = (runtime_folder / "watchdog.py").read_text(
        encoding="utf-8"
    )

    assert "D:\\python\\py311\\python.exe" in start_script
    assert '"%PYTHON_EXE%" watchdog.py' in start_script
    assert "configure_nonblocking_logging" in watchdog_source
    assert "STARTUP_GRACE" in watchdog_source
    assert "FAILURE_THRESHOLD" in watchdog_source
    assert "restart_backoff_seconds" in watchdog_source


@pytest.mark.parametrize(
    ("runtime_key", "child_environment"),
    [
        ("3d", "LG3D_ALGORITHM_3D_WATCHDOG_CHILD"),
        ("2d", "LG3D_ALGORITHM_2D_WATCHDOG_CHILD"),
    ],
)
def test_watchdog_marks_real_algorithm_child(runtime_key, child_environment,
                                             monkeypatch, tmp_path):
    runtime = RUNTIMES[runtime_key]
    watchdog = _load_module(
        runtime["folder"] / "watchdog.py",
        f"algorithm_{runtime_key}_watchdog_test_child_marker",
    )
    captured = {}
    watchdog.HEARTBEAT_FILE = tmp_path / f"{runtime_key}.json"

    def fake_popen(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        return SimpleNamespace(pid=1)

    monkeypatch.setattr(watchdog.subprocess, "Popen", fake_popen)

    watchdog.start_algorithm_process()

    assert captured["kwargs"]["env"][child_environment] == "1"
    assert captured["command"][-1].endswith(("main.py", "server.py"))
