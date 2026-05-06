import argparse
import datetime
import json
import logging
import os
import re
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Sequence
from xml.etree.ElementTree import Element, ElementTree, SubElement

import cv2

ROOT_DIR = Path(__file__).resolve().parents[1]
ALG_2D_DIR = ROOT_DIR / "app" / "algorithm_runtime_2D"
COIL_DB_DIR = ROOT_DIR / "package" / "CoilDataBase"
DEFAULT_MODEL = Path(r"D:\CONFIG_3D\model\CoilDetection_Area_JC.pt")
DEFAULT_SAVE_ROOT = Path(r"D:\CONFIG_3D\debug\area_redetect_latest10000")

for import_path in (ALG_2D_DIR, COIL_DB_DIR):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from configs import CONFIG
from configs.JoinConfig import JoinConfig
from property.DataIntegration import ClipImageItem, DataIntegration


@dataclass
class DetectionBox:
    label: str
    confidence: float
    bbox: tuple[int, int, int, int]


@dataclass
class SavedTile:
    coil_id: int
    surface: str
    area_path: str
    image_path: str
    xml_path: str
    tile_box: tuple[int, int, int, int]
    detections: list[dict]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rerun 2D AREA.jpg detection for latest coils and replace 2D defects in database."
    )
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL, help="YOLO model path.")
    parser.add_argument("--join-config", type=Path, default=CONFIG.JOIN_CONFIG_FILE, help="area_join.json path.")
    parser.add_argument("--limit", type=int, default=10000, help="Latest coil count to process.")
    parser.add_argument(
        "--coil-source",
        choices=["area-folder", "database"],
        default="area-folder",
        help="Where latest coil ids come from.",
    )
    parser.add_argument("--surface", action="append", default=[], help="Surface to process, repeatable. Default all.")
    parser.add_argument("--save-dir", type=Path, default=None, help="Detected tile output folder.")
    parser.add_argument("--metadata", type=Path, default=None, help="Metadata jsonl path.")
    parser.add_argument("--conf", type=float, default=0.25, help="YOLO confidence threshold.")
    parser.add_argument("--imgsz", type=int, default=1024, help="YOLO inference image size.")
    parser.add_argument("--batch-size", type=int, default=32, help="YOLO batch size.")
    parser.add_argument("--device", default="", help="YOLO device, for example 0 or cpu. Empty means automatic.")
    parser.add_argument("--half", action="store_true", help="Use FP16 inference when supported.")
    parser.add_argument("--dry-run", action="store_true", help="Predict only; do not write DB or save images.")
    parser.add_argument("--no-db", action="store_true", help="Do not replace database defects.")
    parser.add_argument("--no-save-images", action="store_true", help="Do not save detected tile images/XML.")
    parser.add_argument(
        "--max-tiles-per-area",
        type=int,
        default=0,
        help="Debug limit for each AREA image. 0 means no limit.",
    )
    return parser.parse_args()


def run_save_dir() -> Path:
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    return DEFAULT_SAVE_ROOT / stamp


def configure_logging(save_dir: Path) -> None:
    save_dir.mkdir(parents=True, exist_ok=True)
    log_path = save_dir / "rerun_2d_area_latest.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def normalize_label(label: str) -> str:
    try:
        fixed_label = label.encode("gbk").decode("utf-8")
    except UnicodeError:
        return label
    return fixed_label or label


def coil_sort_key(coil_id: str | int) -> tuple[int, str]:
    value = str(coil_id)
    if value.isdigit():
        return 0, f"{int(value):020d}"
    return 1, value


def coil_bucket(coil_id: int, bucket_size: int = 10000) -> str:
    return str(int(coil_id) // bucket_size * bucket_size)


def safe_path_name(value: str) -> str:
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value)
    value = value.strip().strip(".")
    return value or "unknown"


def reserve_path(path: Path) -> Path:
    if not path.exists():
        return path
    for index in range(1, 100000):
        candidate = path.with_name(f"{path.stem}_{index}{path.suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"cannot reserve path: {path}")


def existing_area_path(surface_config, coil_id: int) -> Path | None:
    for area_path in (surface_config.get_area_url(coil_id), surface_config.get_area_url_pre(coil_id)):
        if area_path.exists() and area_path.is_file() and area_path.stat().st_size > 0:
            return area_path
    return None


def latest_coils_from_area(join_config: JoinConfig, limit: int) -> list[int]:
    coil_ids = set()
    for surface_config in join_config.surfaces.values():
        save_folder = Path(surface_config.save_folder)
        if not save_folder.exists():
            continue
        numeric_coil_ids = sorted(
            (int(coil_dir.name) for coil_dir in save_folder.iterdir() if coil_dir.is_dir() and coil_dir.name.isdigit()),
            reverse=True,
        )
        surface_found = 0
        for coil_id in numeric_coil_ids:
            if existing_area_path(surface_config, coil_id) is not None:
                coil_ids.add(coil_id)
                surface_found += 1
                if surface_found >= limit:
                    break
    return sorted(coil_ids, reverse=True)[:limit]


def latest_coils_from_database(limit: int) -> list[int]:
    from CoilDataBase.Coil import get_secondary_coil

    coils = get_secondary_coil(limit, desc=True)
    return [int(coil.Id) for coil in coils]


def selected_surfaces(join_config: JoinConfig, surfaces: Sequence[str]) -> dict[str, object]:
    if not surfaces:
        return join_config.surfaces
    selected = {}
    for surface in surfaces:
        surface_key = surface.upper()
        if surface_key not in join_config.surfaces:
            raise KeyError(f"surface not found in join config: {surface_key}")
        selected[surface_key] = join_config.surfaces[surface_key]
    return selected


def load_model(model_path: Path):
    from ultralytics import YOLO

    model = YOLO(str(model_path))
    logging.info("model=%s names=%s", model_path, {key: normalize_label(str(value)) for key, value in model.names.items()})
    return model


def predict_batch(model, clip_items: Sequence[ClipImageItem], args: argparse.Namespace):
    kwargs = {
        "conf": args.conf,
        "imgsz": args.imgsz,
        "verbose": False,
    }
    if args.device:
        kwargs["device"] = args.device
    if args.half:
        kwargs["half"] = True
    return model.predict([item.image for item in clip_items], **kwargs)


def parse_result(result) -> list[DetectionBox]:
    height, width = result.orig_shape[:2]
    detections = []
    for box in result.boxes:
        xyxy = box.xyxy[0].cpu().tolist()
        cls_index = int(box.cls[0].item())
        label = normalize_label(str(result.names.get(cls_index, cls_index)))
        xmin, ymin, xmax, ymax = [int(round(value)) for value in xyxy]
        xmin = max(0, min(width - 1, xmin))
        ymin = max(0, min(height - 1, ymin))
        xmax = max(xmin + 1, min(width, xmax))
        ymax = max(ymin + 1, min(height, ymax))
        detections.append(
            DetectionBox(
                label=label,
                confidence=float(box.conf[0].item()),
                bbox=(xmin, ymin, xmax, ymax),
            )
        )
    return detections


def absolute_defect_box(clip_item: ClipImageItem, detection: DetectionBox) -> tuple[int, int, int, int] | None:
    clip_x1, clip_y1, clip_x2, clip_y2 = clip_item.box
    xmin, ymin, xmax, ymax = detection.bbox
    defect_x1 = min(max(clip_x1 + xmin, clip_x1), clip_x2)
    defect_y1 = min(max(clip_y1 + ymin, clip_y1), clip_y2)
    defect_x2 = min(max(clip_x1 + xmax, clip_x1), clip_x2)
    defect_y2 = min(max(clip_y1 + ymax, clip_y1), clip_y2)
    if defect_x2 <= defect_x1 or defect_y2 <= defect_y1:
        return None
    return int(defect_x1), int(defect_y1), int(defect_x2 - defect_x1), int(defect_y2 - defect_y1)


def build_defect(clip_item: ClipImageItem, detection: DetectionBox) -> dict | None:
    defect_box = absolute_defect_box(clip_item, detection)
    if defect_box is None:
        return None
    defect_x, defect_y, defect_w, defect_h = defect_box
    return {
        "secondaryCoilId": int(clip_item.coil_id),
        "surface": clip_item.surface,
        "defectClass": 101,
        "defectName": "2D_" + detection.label,
        "defectStatus": 5,
        "defectX": defect_x,
        "defectY": defect_y,
        "defectW": defect_w,
        "defectH": defect_h,
        "defectSource": detection.confidence,
        "defectData": "",
    }


def save_pascal_voc_xml(path: Path, image_name: str, width: int, height: int,
                        detections: Sequence[DetectionBox]) -> None:
    annotation = Element("annotation")
    SubElement(annotation, "folder").text = path.parent.name
    SubElement(annotation, "filename").text = image_name
    size = SubElement(annotation, "size")
    SubElement(size, "width").text = str(width)
    SubElement(size, "height").text = str(height)
    SubElement(size, "depth").text = "3"

    for detection in detections:
        obj = SubElement(annotation, "object")
        SubElement(obj, "name").text = detection.label
        SubElement(obj, "confidence").text = f"{detection.confidence:.6f}"
        bbox = SubElement(obj, "bndbox")
        xmin, ymin, xmax, ymax = detection.bbox
        SubElement(bbox, "xmin").text = str(xmin)
        SubElement(bbox, "ymin").text = str(ymin)
        SubElement(bbox, "xmax").text = str(xmax)
        SubElement(bbox, "ymax").text = str(ymax)

    path.parent.mkdir(parents=True, exist_ok=True)
    ElementTree(annotation).write(path, encoding="utf-8", xml_declaration=True)


def save_detected_tile(save_dir: Path, area_path: Path, clip_item: ClipImageItem,
                       detections: Sequence[DetectionBox]) -> SavedTile:
    left, top, right, bottom = clip_item.box
    image_name = f"{clip_item.coil_id}_{clip_item.surface}_x{left}_y{top}_w{right-left}_h{bottom-top}.jpg"
    tile_dir = save_dir / "det" / coil_bucket(int(clip_item.coil_id)) / safe_path_name(clip_item.surface)
    image_path = reserve_path(tile_dir / image_name)
    xml_path = image_path.with_suffix(".xml")

    tile_dir.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(image_path), clip_item.image)
    save_pascal_voc_xml(xml_path, image_path.name, clip_item.image.shape[1], clip_item.image.shape[0], detections)
    return SavedTile(
        coil_id=int(clip_item.coil_id),
        surface=clip_item.surface,
        area_path=str(area_path),
        image_path=str(image_path),
        xml_path=str(xml_path),
        tile_box=(left, top, right, bottom),
        detections=[asdict(detection) for detection in detections],
    )


def append_metadata(metadata_path: Path, saved_tile: SavedTile) -> None:
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    with metadata_path.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(asdict(saved_tile), ensure_ascii=False) + "\n")


def iter_batches(items: Sequence[ClipImageItem], batch_size: int) -> Iterable[Sequence[ClipImageItem]]:
    batch_size = max(1, batch_size)
    for index in range(0, len(items), batch_size):
        yield items[index:index + batch_size]


def load_area(data_integration: DataIntegration, area_path: Path) -> bool:
    image = cv2.imread(str(area_path))
    if image is None:
        return False
    data_integration.set_max_image(image)
    return True


def process_area(model, surface_config, coil_id: int, area_path: Path, save_dir: Path,
                 metadata_path: Path, args: argparse.Namespace) -> tuple[int, int, int]:
    data_integration = DataIntegration(surface_config, coil_id)
    if not load_area(data_integration, area_path):
        logging.warning("skip unreadable area coil=%s surface=%s path=%s", coil_id, surface_config.surface_key, area_path)
        return 0, 0, 1

    clip_items = data_integration.clip_image()
    if args.max_tiles_per_area:
        clip_items = clip_items[:args.max_tiles_per_area]

    defects = []
    hit_tiles = 0
    total_boxes = 0
    for batch in iter_batches(clip_items, args.batch_size):
        results = predict_batch(model, batch, args)
        for clip_item, result in zip(batch, results):
            detections = parse_result(result)
            if not detections:
                continue
            hit_tiles += 1
            total_boxes += len(detections)
            for detection in detections:
                defect = build_defect(clip_item, detection)
                if defect is not None:
                    defects.append(defect)
            if not args.dry_run and not args.no_save_images:
                saved_tile = save_detected_tile(save_dir, area_path, clip_item, detections)
                append_metadata(metadata_path, saved_tile)

    if not args.dry_run and not args.no_db:
        from CoilDataBase.Coil import replace_defects

        replace_defects(defects, coil_id, surface_config.surface_key, "2D_")

    return hit_tiles, total_boxes, 0


def main() -> None:
    args = parse_args()
    save_dir = (args.save_dir or run_save_dir()).resolve()
    metadata_path = (args.metadata or save_dir / "metadata.jsonl").resolve()
    configure_logging(save_dir)

    join_config = JoinConfig(args.join_config)
    surface_configs = selected_surfaces(join_config, args.surface)
    if args.coil_source == "database":
        coil_ids = latest_coils_from_database(args.limit)
    else:
        coil_ids = latest_coils_from_area(join_config, args.limit)

    logging.info("start latest_2d_area limit=%s coils=%s surfaces=%s save_dir=%s dry_run=%s no_db=%s",
                 args.limit, len(coil_ids), ",".join(surface_configs), save_dir, args.dry_run, args.no_db)
    model = load_model(args.model)

    start_time = time.monotonic()
    processed_areas = 0
    skipped_areas = 0
    hit_tiles_total = 0
    boxes_total = 0
    errors = 0

    for index, coil_id in enumerate(coil_ids, start=1):
        for surface_key, surface_config in surface_configs.items():
            area_path = existing_area_path(surface_config, coil_id)
            if area_path is None:
                skipped_areas += 1
                continue
            try:
                hit_tiles, boxes, area_errors = process_area(
                    model, surface_config, coil_id, area_path, save_dir, metadata_path, args
                )
                processed_areas += 1
                hit_tiles_total += hit_tiles
                boxes_total += boxes
                errors += area_errors
            except Exception as exc:
                errors += 1
                logging.exception("failed coil=%s surface=%s path=%s error=%s", coil_id, surface_key, area_path, exc)

        if index == 1 or index % 20 == 0:
            elapsed = time.monotonic() - start_time
            rate = processed_areas / elapsed if elapsed > 0 else 0.0
            logging.info(
                "progress coils=%s/%s processed_areas=%s skipped_areas=%s hit_tiles=%s boxes=%s errors=%s rate=%.2f area/s",
                index,
                len(coil_ids),
                processed_areas,
                skipped_areas,
                hit_tiles_total,
                boxes_total,
                errors,
                rate,
            )

    elapsed = time.monotonic() - start_time
    logging.info(
        "done coils=%s processed_areas=%s skipped_areas=%s hit_tiles=%s boxes=%s errors=%s elapsed_sec=%.1f",
        len(coil_ids),
        processed_areas,
        skipped_areas,
        hit_tiles_total,
        boxes_total,
        errors,
        elapsed,
    )


if __name__ == "__main__":
    exit_code = 0
    try:
        main()
    except Exception:
        exit_code = 1
        logging.exception("rerun_2d_area_latest_coils failed")
    finally:
        logging.shutdown()
    os._exit(exit_code)
