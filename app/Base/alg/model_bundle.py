import os
from pathlib import Path

from Base import CONFIG

MODEL_BUNDLE_VERSION = "LG-Fold-DetectClassify 20260817"
MODEL_BUNDLE_SLUG = "lg_detect_classify_models_v1.0.0_20260729"
DETECTION_INPUT_SIZE = 512
BACKGROUND_CLASS_NAMES = frozenset({"背景"})


def _configured_path(environment_name: str, default: Path) -> Path:
    configured = os.getenv(environment_name)
    if not configured:
        return default

    path = Path(configured).expanduser()
    if not path.is_absolute():
        path = CONFIG.base_config_folder / path
    return path


def model_bundle_root() -> Path:
    default = (CONFIG.base_config_folder / "model" / MODEL_BUNDLE_SLUG)
    return _configured_path("LG3D_UNIFIED_MODEL_DIR", default)


def defect_detector_path() -> Path:
    default = model_bundle_root() / "detection" / "yolo26s_best_defect.pt"
    return _configured_path("LG3D_DEFECT_DETECTOR_MODEL", default)


def defect_classifier_config_path() -> Path:
    default = model_bundle_root() / "runtime" / "classifier.json"
    return _configured_path("LG3D_DEFECT_CLASSIFIER_CONFIG", default)


def is_background_class(class_name: str) -> bool:
    return str(class_name).strip() in BACKGROUND_CLASS_NAMES
