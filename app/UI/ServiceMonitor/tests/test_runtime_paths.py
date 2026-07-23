import json
import sys
from pathlib import Path

from lg3d_service_monitor.config import paths
from lg3d_service_monitor.config.service_registry import (
    load_service_registry,
    monitor_defaults,
)


def test_runtime_paths_use_lg3d_root(monkeypatch, tmp_path):
    monkeypatch.setenv(paths.ENV_LG3D_ROOT, str(tmp_path))
    monkeypatch.delenv(paths.ENV_DATA_DIR, raising=False)

    assert paths.data_root() == (
        tmp_path / "var" / "ServiceMonitor").resolve()
    assert paths.launcher_directory() == (
        tmp_path / "scripts" / "service_control" /
        "launchers").resolve()


def test_runtime_config_does_not_overwrite_existing(monkeypatch, tmp_path):
    data_root = tmp_path / "data"
    monkeypatch.setenv(paths.ENV_DATA_DIR, str(data_root))
    target = data_root / "config" / "SoftMonitor.json"
    target.parent.mkdir(parents=True)
    target.write_text('[{"name": "custom"}]', encoding="utf-8")

    resolved = paths.ensure_runtime_config(
        "SoftMonitor.json",
        default_data=[],
    )

    assert resolved == target.resolve()
    assert json.loads(target.read_text(encoding="utf-8")) == [{
        "name": "custom"
    }]


def test_service_registry_produces_six_monitor_items(monkeypatch, tmp_path):
    source_registry = (
        Path(__file__).resolve().parents[4] /
        "CONFIG_3D" / "service_monitor" / "services.json")
    root = tmp_path / "LG_3D"
    target = root / "CONFIG_3D" / "service_monitor" / "services.json"
    target.parent.mkdir(parents=True)
    target.write_bytes(source_registry.read_bytes())
    monkeypatch.setenv(paths.ENV_LG3D_ROOT, str(root))

    registry = load_service_registry()
    defaults = monitor_defaults()

    assert registry["schemaVersion"] == 1
    assert len(defaults) == 6
    assert {item["key"] for item in defaults} == {
        "main_api",
        "secondary_tcp",
        "plc_write",
        "capture",
        "algorithm_3d",
        "algorithm_2d",
    }


def test_frozen_resources_use_meipass(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)

    assert paths.resources_root() == tmp_path / "resources"
    assert paths.defaults_root() == tmp_path / "config" / "defaults"
