import json
import logging
import os
import sys
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)

CONFIG_FILE_NAME = "PclServerConfig.json"


def _config_candidates() -> list[Path]:
    candidates: list[Path] = []
    configured_path = os.getenv("PLC_SERVER_CONFIG")
    if configured_path:
        candidates.append(Path(configured_path).expanduser())
    if getattr(sys, "frozen", False):
        candidates.append(Path(sys.executable).resolve().parent / CONFIG_FILE_NAME)
    candidates.extend([
        Path.cwd() / CONFIG_FILE_NAME,
        Path(__file__).resolve().with_name(CONFIG_FILE_NAME),
    ])
    unique_candidates: list[Path] = []
    for candidate in candidates:
        if candidate not in unique_candidates:
            unique_candidates.append(candidate)
    return unique_candidates


def _load_config() -> dict[str, Any]:
    for path in _config_candidates():
        if not path.is_file():
            continue
        try:
            with path.open("r", encoding="utf-8") as config_file:
                value = json.load(config_file)
            if not isinstance(value, dict):
                raise ValueError("configuration root must be a JSON object")
            return value
        except (OSError, ValueError, json.JSONDecodeError) as error:
            logger.warning("failed to load PLC config %s: %s", path, error)
    return {}


def _environment_key(key: str) -> str:
    if key in {"server_ip", "server_port"}:
        return f"PLC_{key.upper()}"
    return key.upper()


def _int_setting(data: dict[str, Any], key: str, default: int, minimum: int, maximum: int) -> int:
    raw_value = os.getenv(_environment_key(key), data.get(key, default))
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        logger.warning("invalid PLC config %s=%r; using %s", key, raw_value, default)
        return default
    if not minimum <= value <= maximum:
        logger.warning("out-of-range PLC config %s=%r; using %s", key, raw_value, default)
        return default
    return value


def _float_setting(data: dict[str, Any], key: str, default: float, minimum: float, maximum: float) -> float:
    raw_value = os.getenv(_environment_key(key), data.get(key, default))
    try:
        value = float(raw_value)
    except (TypeError, ValueError):
        logger.warning("invalid PLC config %s=%r; using %s", key, raw_value, default)
        return default
    if not minimum <= value <= maximum:
        logger.warning("out-of-range PLC config %s=%r; using %s", key, raw_value, default)
        return default
    return value


jsData = _load_config()

server_ip = str(os.getenv("PLC_SERVER_IP", jsData.get("server_ip", "0.0.0.0"))).strip() or "0.0.0.0"
server_port = _int_setting(jsData, "server_port", 1035, 1, 65535)
plcForwarderUrl = str(os.getenv("PLC_IP", jsData.get("plc_ip", "192.168.0.1"))).strip() or "192.168.0.1"
plcForwarderRack = _int_setting(jsData, "plc_rack", 0, 0, 255)
plcForwarderSlot = _int_setting(jsData, "plc_slot", 0, 0, 255)
plc_connect_timeout_ms = _int_setting(jsData, "plc_connect_timeout_ms", 2000, 100, 60000)
plc_receive_timeout_ms = _int_setting(jsData, "plc_receive_timeout_ms", 2000, 100, 60000)
plc_operation_lock_timeout_seconds = _float_setting(
    jsData,
    "plc_operation_lock_timeout_seconds",
    6.0,
    0.1,
    300.0,
)
plc_stuck_threshold_seconds = _float_setting(
    jsData,
    "plc_stuck_threshold_seconds",
    20.0,
    1.0,
    3600.0,
)
