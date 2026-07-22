import importlib.util
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WATCHDOG_PATH = PROJECT_ROOT / "app" / "CapTrue" / "watchdog.py"


def _load_watchdog():
    module_name = "capture_service_watchdog_test_module"
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


def test_capture_watchdog_accepts_only_capall_health(monkeypatch):
    module = _load_watchdog()

    monkeypatch.setattr(
        module,
        "urlopen",
        lambda url, timeout: FakeResponse({
            "ok": True,
            "service": "CapAll",
        }),
    )
    assert module.capture_service_healthy(timeout=0.1) is True

    monkeypatch.setattr(
        module,
        "urlopen",
        lambda url, timeout: FakeResponse({
            "ok": True,
            "service": "other",
        }),
    )
    assert module.capture_service_healthy(timeout=0.1) is False


def test_capture_watchdog_treats_connection_failure_as_unhealthy(monkeypatch):
    module = _load_watchdog()

    def connection_failed(url, timeout):
        raise OSError("connection refused")

    monkeypatch.setattr(module, "urlopen", connection_failed)

    assert module.capture_service_healthy(timeout=0.1) is False


def test_capture_watchdog_restarts_exited_child(monkeypatch):
    module = _load_watchdog()

    class FakeProcess:

        def __init__(self, pid, stopped=False):
            self.pid = pid
            self.returncode = 1 if stopped else None
            self.stopped = stopped
            self.terminated = False

        def poll(self):
            return 1 if self.stopped else None

        def terminate(self):
            self.terminated = True
            self.stopped = True
            self.returncode = 0

        def wait(self, timeout):
            return self.returncode

    processes = [FakeProcess(101, stopped=True), FakeProcess(102)]
    started = []

    def start_process():
        process = processes[len(started)]
        started.append(process)
        return process

    sleep_calls = 0

    def bounded_sleep(_seconds):
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls >= 3:
            raise KeyboardInterrupt

    monkeypatch.setattr(module, "start_capture_process", start_process)
    monkeypatch.setattr(module.time, "sleep", bounded_sleep)
    monkeypatch.setattr(module, "STARTUP_GRACE", 999)

    module.supervise_capture_process()

    assert [process.pid for process in started] == [101, 102]
    assert processes[1].terminated is True
