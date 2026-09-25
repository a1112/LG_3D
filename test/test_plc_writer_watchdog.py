import json
import sys
import uuid
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = PROJECT_ROOT / "app"
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from Base.utils.Singleton import SingletonLock
from plcServer import plc_writer_heartbeat, watchdog as plc_bridge_watchdog, write_plc_watchdog


class FakeProcess:
    def __init__(self, pid=1234):
        self.pid = pid


def _heartbeat_payload(*, pid=1234, token="expected", now=100.0):
    return {
        "schemaVersion": 1,
        "service": plc_writer_heartbeat.SERVICE_NAME,
        "pid": pid,
        "watchdogToken": token,
        "updatedAtEpoch": now,
        "status": "ok",
        "activities": [],
    }


def test_runtime_heartbeat_atomically_reports_overdue_activity(tmp_path):
    heartbeat = plc_writer_heartbeat.PlcWriterHeartbeat()
    heartbeat.path = tmp_path / "writer-heartbeat.json"
    token = heartbeat.begin_activity("vendor_plc_read", timeout_seconds=1.0)
    deadline = heartbeat._activities[token]["deadlineAtEpoch"]

    assert heartbeat.write_once(now=deadline + 1.0)
    payload = json.loads(heartbeat.path.read_text(encoding="utf-8"))

    assert payload["status"] == "stalled"
    assert payload["overdueActivities"][0]["name"] == "vendor_plc_read"


def test_runtime_heartbeat_tracks_live_watchdog_parent(monkeypatch):
    monkeypatch.setenv(plc_writer_heartbeat.WATCHDOG_PID_ENV, str(write_plc_watchdog.os.getpid()))
    heartbeat = plc_writer_heartbeat.PlcWriterHeartbeat()

    assert heartbeat.watchdog_pid == write_plc_watchdog.os.getpid()
    assert heartbeat._process_alive(heartbeat.watchdog_pid) is True


def test_watchdog_requires_fresh_matching_process_and_token(tmp_path, monkeypatch):
    path = tmp_path / "writer-heartbeat.json"
    path.write_text(json.dumps(_heartbeat_payload()), encoding="utf-8")
    monkeypatch.setattr(write_plc_watchdog, "HEARTBEAT_TIMEOUT", 10.0)

    healthy, reason = write_plc_watchdog.heartbeat_health(
        FakeProcess(),
        "expected",
        path=path,
        now=105.0,
    )
    assert (healthy, reason) == (True, "ok")

    wrong_pid, reason = write_plc_watchdog.heartbeat_health(
        FakeProcess(pid=4321),
        "expected",
        path=path,
        now=105.0,
    )
    assert wrong_pid is False
    assert reason == "heartbeat_pid_mismatch"

    wrong_token, reason = write_plc_watchdog.heartbeat_health(
        FakeProcess(),
        "other",
        path=path,
        now=105.0,
    )
    assert wrong_token is False
    assert reason == "heartbeat_token_mismatch"


def test_watchdog_rejects_fresh_heartbeat_with_overdue_activity(tmp_path):
    path = tmp_path / "writer-heartbeat.json"
    payload = _heartbeat_payload(now=100.0)
    payload["activities"] = [{
        "name": "database_write_plc_snapshot",
        "deadlineAtEpoch": 104.0,
    }]
    path.write_text(json.dumps(payload), encoding="utf-8")

    healthy, reason = write_plc_watchdog.heartbeat_health(
        FakeProcess(),
        "expected",
        path=path,
        now=105.0,
    )

    assert healthy is False
    assert reason == "heartbeat_activity_overdue:database_write_plc_snapshot"


def test_watchdog_starts_marked_child_in_separate_process_group(monkeypatch, tmp_path):
    captured = {}

    class StartedProcess:
        pid = 2468

    def fake_popen(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        return StartedProcess()

    monkeypatch.setattr(write_plc_watchdog, "HEARTBEAT_FILE", tmp_path / "heartbeat.json")
    monkeypatch.setattr(write_plc_watchdog.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(write_plc_watchdog.sys, "platform", "win32")

    process = write_plc_watchdog.start_writer_process()

    assert captured["kwargs"]["env"][write_plc_watchdog.CHILD_ENVIRONMENT] == "1"
    assert captured["kwargs"]["env"][plc_writer_heartbeat.WATCHDOG_TOKEN_ENV]
    assert captured["kwargs"]["env"][plc_writer_heartbeat.WATCHDOG_PID_ENV] == str(
        write_plc_watchdog.os.getpid()
    )
    assert captured["kwargs"]["creationflags"] == write_plc_watchdog.subprocess.CREATE_NEW_PROCESS_GROUP
    assert process.watchdog_token == captured["kwargs"]["env"][plc_writer_heartbeat.WATCHDOG_TOKEN_ENV]
    assert captured["command"][-1].endswith("writePLC.py")


def test_writer_source_auto_bootstraps_and_has_independent_singleton():
    source = (PROJECT_ROOT / "app/plcServer/writePLC.py").read_text(encoding="utf-8")
    watchdog_source = (
        PROJECT_ROOT / "app/plcServer/write_plc_watchdog.py"
    ).read_text(encoding="utf-8")

    assert "maybe_exec_watchdog(" in source
    assert "LG3D_PLC_WRITER_WATCHDOG_CHILD" in source
    assert '"plc_width_writer"' in source
    assert '"plc_width_writer_watchdog"' in watchdog_source
    assert "begin_activity(\"runtime_imports\")" in source


def test_frozen_writer_bundle_contains_watchdog_modules():
    spec = (PROJECT_ROOT / "app/plcServer/writePLC.spec").read_text(encoding="utf-8")

    assert "'write_plc_watchdog'" in spec
    assert "'plc_writer_heartbeat'" in spec
    assert "'Base.utils.Singleton'" in spec


def test_writer_watchdog_singleton_rejects_second_process(tmp_path):
    lock_name = f"plc_writer_watchdog_test_{uuid.uuid4().hex}"
    first = SingletonLock(lock_name, pid_dir=tmp_path)
    second = SingletonLock(lock_name, pid_dir=tmp_path)

    try:
        assert first.acquire() is True
        assert second.acquire() is False
    finally:
        second.release()
        first.release()


def test_plc_watchdogs_use_global_windows_mutex_namespace():
    bridge_source = (
        PROJECT_ROOT / "app/plcServer/watchdog.py"
    ).read_text(encoding="utf-8")
    singleton_source = (
        PROJECT_ROOT / "app/Base/utils/Singleton.py"
    ).read_text(encoding="utf-8")

    assert 'WATCHDOG_MUTEX_NAME = "Global\\\\LG3D_PLC_Watchdog"' in bridge_source
    assert 'f"Global\\\\{self.name}"' in singleton_source


def test_plc_bridge_global_mutex_rejects_second_watchdog(monkeypatch):
    if sys.platform != "win32":
        return

    # Use a unique global name without touching any running production lock.
    unique_name = f"Global\\LG3D_PLC_Watchdog_Test_{uuid.uuid4().hex}"
    monkeypatch.setattr(plc_bridge_watchdog, "WATCHDOG_MUTEX_NAME", unique_name)
    first = plc_bridge_watchdog.acquire_instance_lock()
    try:
        assert first is not None
        assert plc_bridge_watchdog.acquire_instance_lock() is None
    finally:
        plc_bridge_watchdog.release_instance_lock(first)
