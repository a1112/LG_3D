import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any


ENV_LG3D_ROOT = "LG3D_ROOT"
ENV_DATA_DIR = "LG3D_MONITOR_DATA_DIR"
ENV_LAUNCHER_DIR = "LG3D_SERVICE_LAUNCHER_DIR"
ENV_READ_ONLY = "LG3D_MONITOR_READ_ONLY"


def _source_project_root() -> Path:
    return Path(__file__).resolve().parents[6]


def lg3d_root() -> Path:
    configured = os.getenv(ENV_LG3D_ROOT, "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    if not getattr(sys, "frozen", False):
        source_root = _source_project_root()
        if (source_root / "CONFIG_3D").is_dir():
            return source_root
    return Path(r"D:\LCX_USER\LG_3D")


def project_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parents[3]


def resources_root() -> Path:
    base = Path(getattr(sys, "_MEIPASS", project_root()))
    return base / "resources"


def defaults_root() -> Path:
    base = Path(getattr(sys, "_MEIPASS", project_root()))
    return base / "config" / "defaults"


def data_root() -> Path:
    configured = os.getenv(ENV_DATA_DIR, "").strip()
    root = Path(configured).expanduser() if configured else (
        lg3d_root() / "var" / "ServiceMonitor")
    return root.resolve()


def runtime_config_dir() -> Path:
    return data_root() / "config"


def log_directory(name: str) -> Path:
    return data_root() / "logs" / name


def pid_file() -> Path:
    return data_root() / "service-monitor.pid.json"


def active_release_file() -> Path:
    return data_root() / "active.json"


def launcher_directory() -> Path:
    configured = os.getenv(ENV_LAUNCHER_DIR, "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return (lg3d_root() / "scripts" / "service_control" /
            "launchers").resolve()


def service_registry_path() -> Path:
    return (lg3d_root() / "CONFIG_3D" / "service_monitor" /
            "services.json").resolve()


def bundled_registry_path() -> Path:
    return defaults_root() / "services.json"


def resolve_lg3d_path(value: str | os.PathLike[str]) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (lg3d_root() / path).resolve()


def is_read_only() -> bool:
    return os.getenv(ENV_READ_ONLY, "").strip().casefold() in {
        "1", "true", "yes", "on"
    }


def legacy_config_directories() -> list[Path]:
    root = lg3d_root()
    legacy_root = root.parent / "bkvl_UI"
    return [
        legacy_root / "dist" / "lis" / "config",
        legacy_root / "config",
    ]


def ensure_runtime_config(
    name: str,
    *,
    default_data: Any,
    default_file: Path | None = None,
) -> Path:
    target = runtime_config_dir() / name
    if target.exists():
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    for directory in legacy_config_directories():
        candidate = directory / name
        if candidate.is_file():
            shutil.copy2(candidate, target)
            return target
    candidate = default_file or (defaults_root() / name)
    if candidate.is_file():
        shutil.copy2(candidate, target)
    else:
        target.write_text(
            json.dumps(default_data, ensure_ascii=False, indent=4),
            encoding="utf-8",
        )
    return target


def ensure_runtime_directories() -> None:
    for path in (
        data_root(),
        runtime_config_dir(),
        data_root() / "logs",
    ):
        path.mkdir(parents=True, exist_ok=True)
