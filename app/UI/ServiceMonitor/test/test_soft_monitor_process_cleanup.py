from ProcessObj.SoftMonitor import SoftMonitor


def _monitor(item):
    monitor = SoftMonitor.__new__(SoftMonitor)
    monitor.monitorData = [item]
    return monitor


def test_target_pids_adopt_port_listener_and_watchdog_parent(monkeypatch):
    item = {
        "name": "api",
        "exe": "start_api.bat",
        "heartbeatPort": 5010,
    }
    monitor = _monitor(item)
    monkeypatch.setattr(
        "ProcessObj.SoftMonitor.globSoftConfig.get_pid_list", lambda _: [])
    monkeypatch.setattr(
        "ProcessObj.SoftMonitor.getProcessesByTargets", lambda _: [])
    monkeypatch.setattr(
        "ProcessObj.SoftMonitor.get_listening_pids", lambda port: [101])
    monkeypatch.setattr(
        "ProcessObj.SoftMonitor.get_process_ids_from_files", lambda paths: [])
    observed = {}

    def fake_roots(process_ids):
        observed["process_ids"] = process_ids
        return [100]

    monkeypatch.setattr(
        "ProcessObj.SoftMonitor.get_process_tree_roots", fake_roots)

    result = monitor._get_target_pids("start_api.bat", item)

    assert observed["process_ids"] == [101]
    assert result == [100]


def test_target_pids_uses_persisted_worker_pid_files(monkeypatch):
    item = {
        "name": "algorithm",
        "exe": "start_algorithm.bat",
        "processPidFiles": ["runtime_heartbeat.json"],
    }
    monitor = _monitor(item)
    monkeypatch.setattr(
        "ProcessObj.SoftMonitor.globSoftConfig.get_pid_list", lambda _: [])
    monkeypatch.setattr(
        "ProcessObj.SoftMonitor.getProcessesByTargets", lambda _: [])
    monkeypatch.setattr(
        "ProcessObj.SoftMonitor.get_listening_pids", lambda port: [])
    monkeypatch.setattr(
        "ProcessObj.SoftMonitor.get_process_ids_from_files",
        lambda paths: [201])
    monkeypatch.setattr(
        "ProcessObj.SoftMonitor.get_process_tree_roots",
        lambda process_ids: [200])

    assert monitor._get_target_pids("start_algorithm.bat", item) == [200]
