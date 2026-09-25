import importlib.util
import logging
import sys
import threading
import time
from pathlib import Path
from types import ModuleType, SimpleNamespace


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CORE_PATH = PROJECT_ROOT / "app" / "CapTrue" / "core.py"


def _load_core(monkeypatch, harvester_class, camera_configs=None):
    config_module = ModuleType("CONFIG")
    config_module.capTureConfig = SimpleNamespace(
        SICKGigEVisionTL="SICKGigEVisionTL.cti",
        camera_config_list=camera_configs or [],
    )
    global_module = ModuleType("Global")
    global_module.USE_3D = True
    log_module = ModuleType("Log")
    log_module.logger = logging.getLogger("test.capture_core")
    harvesters_package = ModuleType("harvesters")
    harvesters_package.__path__ = []
    harvesters_core = ModuleType("harvesters.core")
    harvesters_core.Harvester = harvester_class

    monkeypatch.setitem(sys.modules, "CONFIG", config_module)
    monkeypatch.setitem(sys.modules, "Global", global_module)
    monkeypatch.setitem(sys.modules, "Log", log_module)
    monkeypatch.setitem(sys.modules, "harvesters", harvesters_package)
    monkeypatch.setitem(sys.modules, "harvesters.core", harvesters_core)

    module_name = "capture_core_recovery_test"
    spec = importlib.util.spec_from_file_location(module_name, CORE_PATH)
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, module_name, module)
    spec.loader.exec_module(module)
    return module


def test_missing_camera_candidate_reuses_cached_device_index(monkeypatch):

    class FakeHarvester:

        def __init__(self):
            self.device_info_list = [
                SimpleNamespace(
                    display_name="SICK Ranger3",
                    serial_number="24170059",
                    model="Ranger3",
                    tl_type="GEV",
                )
            ]
            self.update_calls = 0
            self.create_calls = 0
            self.list_indexes = []

        def add_file(self, path):
            self.path = path

        def update(self):
            self.update_calls += 1

        def create_image_acquirer(self,
                                  serial_number=None,
                                  list_index=None):
            self.create_calls += 1
            if self.create_calls == 1:
                raise RuntimeError("You have no candidate.")
            self.list_indexes.append(list_index)
            return {
                "serialNumber":
                self.device_info_list[list_index].serial_number
            }

    module = _load_core(monkeypatch, FakeHarvester)

    camera = module.get_camera_by_sn("24170059")

    assert camera == {"serialNumber": "24170059"}
    assert module.h.update_calls == 1
    assert module.h.create_calls == 2
    assert module.h.list_indexes == [0]


def test_harvester_camera_creation_is_serialized(monkeypatch):

    class FakeHarvester:

        def __init__(self):
            self.device_info_list = [
                SimpleNamespace(
                    display_name="camera",
                    serial_number=f"camera-{index}",
                    model="Ranger3",
                    tl_type="GEV",
                ) for index in range(4)
            ]
            self.active_creates = 0
            self.max_active_creates = 0

        def add_file(self, path):
            return None

        def update(self):
            return None

        def create_image_acquirer(self, serial_number=None, list_index=None):
            self.active_creates += 1
            self.max_active_creates = max(
                self.max_active_creates, self.active_creates)
            time.sleep(0.02)
            self.active_creates -= 1
            return serial_number

    module = _load_core(monkeypatch, FakeHarvester)
    threads = [
        threading.Thread(
            target=module.get_camera_by_sn,
            args=(f"camera-{index}", ),
        ) for index in range(4)
    ]

    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=1)

    assert module.h.max_active_creates == 1
