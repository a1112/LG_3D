import importlib.util
import logging
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SIGNAL_PATH = PROJECT_ROOT / "app" / "CapTrue" / "Signal.py"


def _load_signal(monkeypatch, get_last_coil):
    config = ModuleType("CONFIG")
    config.capTureConfig = SimpleNamespace(signalUrl="unused")

    coil_package = ModuleType("CoilDataBase")
    coil_package.__path__ = []
    coil_module = ModuleType("CoilDataBase.Coil")
    coil_module.get_last_coil = get_last_coil
    coil_package.Coil = coil_module
    models_package = ModuleType("CoilDataBase.models")
    models_package.__path__ = []
    secondary_module = ModuleType("CoilDataBase.models.SecondaryCoil")
    secondary_module.SecondaryCoil = object
    log_module = ModuleType("Log")
    log_module.logger = logging.getLogger("test.capture_signal")

    for name, module in {
            "CONFIG": config,
            "CoilDataBase": coil_package,
            "CoilDataBase.Coil": coil_module,
            "CoilDataBase.models": models_package,
            "CoilDataBase.models.SecondaryCoil": secondary_module,
            "Log": log_module,
    }.items():
        monkeypatch.setitem(sys.modules, name, module)

    module_name = "capture_signal_resilience_test_module"
    spec = importlib.util.spec_from_file_location(module_name, SIGNAL_PATH)
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, module_name, module)
    spec.loader.exec_module(module)
    return module


def test_coil_switch_is_committed_after_bounded_quiet_wait(monkeypatch):
    old_coil = SimpleNamespace(CoilNo="OLD", Id=1)
    new_coil = SimpleNamespace(CoilNo="NEW", Id=2)
    calls = [0]

    def get_last_coil():
        calls[0] += 1
        return old_coil if calls[0] == 1 else new_coil

    module = _load_signal(monkeypatch, get_last_coil)
    module.SIGNAL_SWITCH_MAX_WAIT_SECONDS = 2.0
    module.lastTimeDict.clear()
    module.lastTimeDict["camera"] = 100.0
    clock = [100.0]
    events = []

    monkeypatch.setattr(module.time, "time", lambda: clock[0])
    monkeypatch.setattr(module.time, "monotonic", lambda: clock[0])

    def advance(seconds):
        clock[0] += seconds
        if events and events[-1] == ("in", "NEW"):
            raise KeyboardInterrupt

    monkeypatch.setattr(module.time, "sleep", advance)
    listener = module.Signal("unused")
    listener.register(
        lambda event, coil: events.append((event, coil.CoilNo)))

    with pytest.raises(KeyboardInterrupt):
        listener.run()

    assert events == [
        ("init", "OLD"),
        ("out", "OLD"),
        ("in", "NEW"),
    ]
    assert listener.coil is new_coil


def test_signal_status_exposes_stalled_database_poll(monkeypatch):
    module = _load_signal(monkeypatch, lambda: None)
    listener = module.Signal("unused")
    listener.last_poll_started_at = 10.0
    listener.last_poll_started_monotonic = 10.0
    monkeypatch.setattr(module.time, "monotonic",
                        lambda: 10.0 + module.SIGNAL_POLL_STALL_SECONDS + 0.1)

    status = listener.get_status()

    assert status["pollAge"] > module.SIGNAL_POLL_STALL_SECONDS
    assert status["stalled"] is True
