import os
from typing import Sequence


LOG_MODEL_NAMES = frozenset({
    "CapTrueLog",
    "CapTrueLogItem",
    "DetectionSpeed",
    "ImageJoinLog",
    "ServerDetectionError",
})

RAW_MODEL_NAMES = frozenset({
    "LineData",
})


def _env_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _extra_skip_model_names() -> set[str]:
    value = os.getenv("COIL_DATABASE_SKIP_MODELS", "")
    return {item.strip() for item in value.split(",") if item.strip()}


def disabled_storage_model_names() -> set[str]:
    disabled = set(_extra_skip_model_names())
    if not should_store_log_data():
        disabled.update(LOG_MODEL_NAMES)
    if not should_store_raw_data():
        disabled.update(RAW_MODEL_NAMES)
    return disabled


def should_store_model_name(model_name: str) -> bool:
    return model_name not in disabled_storage_model_names()


def should_store_model(obj) -> bool:
    return should_store_model_name(obj.__class__.__name__)


def filter_storable_objects(objs: Sequence) -> list:
    disabled = disabled_storage_model_names()
    return [obj for obj in objs if obj.__class__.__name__ not in disabled]


def should_store_point_raw_fields() -> bool:
    return _env_flag("COIL_STORE_POINT_RAW_DATA", False)


def should_store_log_data() -> bool:
    return _env_flag("COIL_STORE_LOG_DATA", False)


def should_store_raw_data() -> bool:
    return _env_flag("COIL_STORE_RAW_DATA", False)


def should_store_capture_raw_files() -> bool:
    return _env_flag("COIL_STORE_CAPTURE_RAW_FILES", True)


def skipped_table_names_for_log_and_raw() -> set[str]:
    return set(LOG_MODEL_NAMES | RAW_MODEL_NAMES)
