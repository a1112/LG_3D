from types import SimpleNamespace
from threading import Lock

from lg3d_service_monitor.monitoring.services import SoftMonitor


def _monitor():
    monitor = SoftMonitor.__new__(SoftMonitor)
    monitor.heartbeatFailedSince = {}
    monitor.heartbeatLastCheckedAt = {}
    monitor.manualStopped = set()
    monitor.log = SimpleNamespace(
        info=lambda *_: None,
        warning=lambda *_: None,
        error=lambda *_: None,
    )
    return monitor


def test_heartbeat_restarts_only_after_200_seconds(monkeypatch):
    monitor = _monitor()
    restarts = []
    item = {"name": "capture", "heartbeatPort": 6100}
    now = [1000.0]
    monkeypatch.setattr(
        "lg3d_service_monitor.monitoring.services.time.monotonic",
        lambda: now[0],
    )
    monkeypatch.setattr(monitor, "_heartbeat_healthy", lambda _: False)
    monkeypatch.setattr(monitor, "restartExe", restarts.append)

    monitor._check_heartbeat(item)
    now[0] += 199
    monitor._check_heartbeat(item)
    assert restarts == []

    now[0] += 1
    monitor._check_heartbeat(item)
    assert restarts == ["capture"]


def test_heartbeat_recovery_clears_failure_timer(monkeypatch):
    monitor = _monitor()
    item = {"name": "api", "heartbeatPort": 5010}
    monitor.heartbeatFailedSince["api"] = 500.0
    monkeypatch.setattr(monitor, "_heartbeat_healthy", lambda _: True)

    monitor._check_heartbeat(item)

    assert "api" not in monitor.heartbeatFailedSince


def test_restart_request_returns_before_worker_runs(monkeypatch):
    monitor = _monitor()
    monitor.monitorData = [{
        "name": "api",
        "exe": "C:/services/api.bat",
        "args": "",
    }]
    monitor.restartLock = Lock()
    monitor.restarting = set()
    workers = []

    class PendingThread:
        def __init__(self, target, args, **_):
            self.target = target
            self.args = args

        def start(self):
            workers.append(self)

    monkeypatch.setattr(
        "lg3d_service_monitor.monitoring.services.Thread",
        PendingThread,
    )
    monkeypatch.setattr(monitor, "_resolve_exe_path", lambda value: value)
    monkeypatch.setattr(monitor, "_stop_target", lambda *_: True)
    monkeypatch.setattr(monitor, "_start_exe_", lambda *_: 33)
    monkeypatch.setattr(
        "lg3d_service_monitor.monitoring.services.time.sleep",
        lambda _: None,
    )

    assert monitor.restartExe("api") is True
    assert len(workers) == 1
    assert monitor.restartExe("api") is False
    assert "c:\\services\\api.bat" in monitor.restarting

    workers[0].target(*workers[0].args)

    assert monitor.restarting == set()


def test_heartbeat_uses_configured_timeout(monkeypatch):
    monitor = _monitor()
    restarts = []
    item = {
        "name": "capture",
        "heartbeatPort": 6100,
        "heartbeatTimeoutSeconds": 30,
    }
    now = [1000.0]
    monkeypatch.setattr(
        "lg3d_service_monitor.monitoring.services.time.monotonic",
        lambda: now[0],
    )
    monkeypatch.setattr(monitor, "_heartbeat_healthy", lambda _: False)
    monkeypatch.setattr(monitor, "restartExe", restarts.append)

    monitor._check_heartbeat(item)
    now[0] += 29
    monitor._check_heartbeat(item)
    assert restarts == []
    now[0] += 1
    monitor._check_heartbeat(item)
    assert restarts == ["capture"]


def test_heartbeat_text_contains_last_check_time_and_timeout(monkeypatch):
    monitor = _monitor()
    monitor.monitorData = [{
        "name": "api",
        "exe": "C:/services/api.bat",
        "heartbeatPort": 5010,
        "heartbeatTimeoutSeconds": 200,
    }]
    monitor.heartbeatLastCheckedAt["api"] = 123.0
    monkeypatch.setattr(
        "lg3d_service_monitor.monitoring.services.time.strftime",
        lambda *_: "12:34:56",
    )

    text = monitor.getHeartbeatText("api")


def test_read_only_mode_blocks_restart(monkeypatch):
    monitor = _monitor()
    monitor.monitorData = [{
        "name": "api",
        "exe": "start_lg3d_api_source.bat",
    }]
    monkeypatch.setenv("LG3D_MONITOR_READ_ONLY", "1")

    assert monitor.restartExe("api") is False
