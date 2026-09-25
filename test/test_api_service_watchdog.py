import importlib.util
import json
from pathlib import Path
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WATCHDOG_PATH = PROJECT_ROOT / "app" / "Server" / "watchdog.py"


def _load_watchdog():
    module_name = "api_service_watchdog_test_module"
    spec = importlib.util.spec_from_file_location(module_name, WATCHDOG_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class FakeResponse:
    def __init__(self, payload, status=200):
        self.status = status
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def test_api_watchdog_accepts_only_api_health(monkeypatch):
    module = _load_watchdog()
    monkeypatch.setattr(
        module,
        "urlopen",
        lambda url, timeout: FakeResponse({
            "ok": True,
            "service": "LG3D_API",
        }),
    )
    assert module.api_service_healthy(timeout=0.1) is True

    monkeypatch.setattr(
        module,
        "urlopen",
        lambda url, timeout: FakeResponse({
            "ok": True,
            "service": "other",
        }),
    )
    assert module.api_service_healthy(timeout=0.1) is False


def test_api_watchdog_treats_connection_failure_as_unhealthy(monkeypatch):
    module = _load_watchdog()

    def connection_failed(url, timeout):
        raise OSError("connection refused")

    monkeypatch.setattr(module, "urlopen", connection_failed)
    assert module.api_service_healthy(timeout=0.1) is False


def test_api_watchdog_restart_backoff_is_bounded(monkeypatch):
    module = _load_watchdog()
    monkeypatch.setattr(module, "RESTART_DELAY", 5)
    monkeypatch.setattr(module, "RESTART_MAX_DELAY", 60)

    assert module.restart_backoff(1) == 5
    assert module.restart_backoff(2) == 10
    assert module.restart_backoff(4) == 40
    assert module.restart_backoff(20) == 60


def test_api_watchdog_starts_child_in_own_process_group(monkeypatch):
    module = _load_watchdog()
    captured = {}

    def fake_popen(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        return object()

    monkeypatch.setattr(module.sys, "platform", "linux")
    monkeypatch.setattr(module.subprocess, "Popen", fake_popen)

    module.start_api_process()

    assert captured["kwargs"]["start_new_session"] is True
    assert captured["kwargs"]["env"]["LG3D_API_WATCHDOG_CHILD"] == "1"
    assert captured["command"][-1].endswith("Server.py")


def test_api_watchdog_uses_tree_kill_immediately_on_windows(monkeypatch):
    module = _load_watchdog()
    tree_kills = []

    class StuckProcess:
        pid = 123

        def __init__(self):
            self.terminate_calls = 0

        def poll(self):
            return None

        def terminate(self):
            self.terminate_calls += 1

        def wait(self, timeout):
            return 0

    process = StuckProcess()
    monkeypatch.setattr(module.sys, "platform", "win32")
    monkeypatch.setattr(module, "_force_kill_process_tree",
                        lambda item: tree_kills.append(item.pid))

    module.stop_api_process(process)

    assert tree_kills == [123]
    assert process.terminate_calls == 0


def test_api_watchdog_uses_tree_kill_after_stop_timeout_on_posix(monkeypatch):
    module = _load_watchdog()
    tree_kills = []

    class StuckProcess:
        pid = 456

        def __init__(self):
            self.wait_calls = 0

        def poll(self):
            return None

        def terminate(self):
            return None

        def wait(self, timeout):
            self.wait_calls += 1
            if self.wait_calls == 1:
                raise subprocess.TimeoutExpired("api", timeout)
            return 0

    process = StuckProcess()
    monkeypatch.setattr(module.sys, "platform", "linux")
    monkeypatch.setattr(module, "_force_kill_process_tree",
                        lambda item: tree_kills.append(item.pid))

    module.stop_api_process(process)

    assert tree_kills == [456]
