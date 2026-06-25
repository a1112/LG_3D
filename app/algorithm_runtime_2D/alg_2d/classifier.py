import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

from PIL import Image

from configs import CONFIG
from utils.MultiprocessColorLogger import logger


AREA_DEFECT_NAME_PREFIX = "2D_"
DEFAULT_2D_DEFECT_CLASS = 101

_classifier_model = None
_classifier_load_failed = False


@dataclass
class ClassificationResult:
    label: int
    source: float
    name: str


def area_defect_name(name: str) -> str:
    name = str(name)
    if name.startswith(AREA_DEFECT_NAME_PREFIX):
        return name
    return AREA_DEFECT_NAME_PREFIX + name


def _ensure_app_path() -> None:
    app_path = Path(__file__).resolve().parents[2]
    app_path_text = str(app_path)
    if app_path_text not in sys.path:
        sys.path.insert(0, app_path_text)


def _resolve_classifier_config(config_path: Optional[str]) -> Optional[Path]:
    if not config_path:
        return None

    path = Path(config_path)
    if path.is_absolute() and path.exists():
        return path

    candidates = [
        Path.cwd() / path,
        CONFIG.base_config_folder / path,
        CONFIG.base_config_folder / "model" / path,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate

    return path


def _create_classifier_model():
    _ensure_app_path()
    from Base.alg.CoilClsModel import CoilClsModel

    config_path = _resolve_classifier_config(CONFIG.classifier_config)
    if config_path is not None:
        return CoilClsModel(config=config_path)

    try:
        return CoilClsModel()
    except Exception as e:
        fallback_config = CONFIG.base_config_folder / "model" / "CoilClassifiersConfig.json"
        if fallback_config.exists():
            logger.warning(
                f"2D classifier default config failed, try fallback {fallback_config}: {e}"
            )
            return CoilClsModel(config=fallback_config)
        raise e


def _get_classifier_model():
    global _classifier_load_failed
    global _classifier_model

    if not CONFIG.enable_classifier or _classifier_load_failed:
        return None
    if _classifier_model is not None:
        return _classifier_model

    try:
        _classifier_model = _create_classifier_model()
        logger.info("2D classifier loaded")
    except Exception as e:
        _classifier_load_failed = True
        logger.error(f"2D classifier load failed: {e}")
    return _classifier_model


def _expand_box(
        image_size: tuple[int, int],
        xmin: int,
        ymin: int,
        xmax: int,
        ymax: int,
) -> tuple[int, int, int, int] | None:
    image_width, image_height = image_size
    box_width = xmax - xmin
    box_height = ymax - ymin
    if box_width <= 0 or box_height <= 0:
        return None

    margin_w = CONFIG.classifier_crop_margin
    margin_h = CONFIG.classifier_crop_margin
    if box_width < CONFIG.classifier_crop_min_size:
        margin_w = max(margin_w, (CONFIG.classifier_crop_min_size - box_width) // 2)
    if box_height < CONFIG.classifier_crop_min_size:
        margin_h = max(margin_h, (CONFIG.classifier_crop_min_size - box_height) // 2)

    crop_xmin = max(xmin - margin_w, 0)
    crop_ymin = max(ymin - margin_h, 0)
    crop_xmax = min(xmax + margin_w, image_width)
    crop_ymax = min(ymax + margin_h, image_height)
    if crop_xmax <= crop_xmin or crop_ymax <= crop_ymin:
        return None
    return crop_xmin, crop_ymin, crop_xmax, crop_ymax


def _to_pil_image(image) -> Image.Image:
    if isinstance(image, Image.Image):
        return image
    return Image.fromarray(image)


def classify_boxes(source_image, boxes: Sequence[tuple[int, int, int, int]]) -> list[ClassificationResult | None]:
    results: list[ClassificationResult | None] = [None] * len(boxes)
    if not CONFIG.enable_classifier or source_image is None or not boxes:
        return results

    pil_image = _to_pil_image(source_image)
    crop_images = []
    crop_indexes = []
    for index, (x, y, w, h) in enumerate(boxes):
        crop_box = _expand_box(pil_image.size, x, y, x + w, y + h)
        if crop_box is None:
            continue
        crop_images.append(pil_image.crop(crop_box))
        crop_indexes.append(index)

    if not crop_images:
        return results

    classifier_model = _get_classifier_model()
    if classifier_model is None:
        return results

    try:
        res_index, res_source, names = classifier_model.predict_image(crop_images)
    except Exception as e:
        logger.error(f"2D classifier predict failed: {e}")
        return results

    for index, label, source, name in zip(crop_indexes, res_index, res_source, names):
        results[index] = ClassificationResult(label, source, name)
    return results
