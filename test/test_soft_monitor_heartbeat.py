from types import SimpleNamespace

from ProcessObj.SoftMonitor import SoftMonitor


def _monitor():
    monitor = SoftMonitor.__new__(SoftMonitor)
    monitor.heartbeatFailedSince = {}
    monitor.log = SimpleNamespace(info=lambda *_: None, error=lambda *_: None)
    return monitor


def test_heartbeat_restarts_only_after_200_seconds(monkeypatch):
    monitor = _monitor()
    restarts = []
    item = {"name": "capture", "heartbeatPort": 6100}
    now = [1000.0]
    monkeypatch.setattr("ProcessObj.SoftMonitor.time.monotonic", lambda: now[0])
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
