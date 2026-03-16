import argparse
import itertools
import math
import os
import sys
import threading
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from pathlib import Path
from typing import Iterable, List, Sequence
from xml.etree.ElementTree import Element, ElementTree, SubElement

from PIL import Image


APP_DIR = (Path(__file__).resolve().parents[1] / "app").resolve()
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from Base.alg.CoilClsModel import CoilClsModel


CLASS_NAMES = [
    "背景",
    "刮丝",
    "小型缺陷",
    "折叠",
    "毛刺",
    "烂边",
    "脏污",
    "边部褶皱",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Split jpg/GRAY.jpg into 10x10 tiles, detect, classify, and save jpg+xml into classifier folders."
    )
    parser.add_argument("--model", default=r"D:\CONFIG_3D\model\yolo26best.pt", help="YOLO model path.")
    parser.add_argument(
        "--classifier-config",
        default=r"D:\CONFIG_3D\model\classifier\classifier.json",
        help="Classifier config path.",
    )
    parser.add_argument(
        "--inputs",
        nargs="+",
        default=[r"D:\Save_S", r"E:\Save_L"],
        help="Input roots to scan for jpg/GRAY.jpg.",
    )
    parser.add_argument("--output", default=r"D:\检出优化\0313", help="Output root folder.")
    parser.add_argument("--rows", type=int, default=10, help="Tile rows.")
    parser.add_argument("--cols", type=int, default=10, help="Tile cols.")
    parser.add_argument("--conf", type=float, default=0.25, help="Detection confidence threshold.")
    parser.add_argument("--imgsz", type=int, default=640, help="YOLO inference image size.")
    parser.add_argument("--workers", type=int, default=10, help="Worker threads for CPU/I/O pipeline.")
    parser.add_argument(
        "--cpu-threads",
        type=int,
        default=max(1, min(os.cpu_count() or 1, 10)),
        help="Torch/OpenMP CPU thread count.",
    )
    parser.add_argument("--limit", type=int, default=0, help="Max source images to process. 0 means no limit.")
    parser.add_argument(
        "--start-coil-id",
        default="",
        help="Resume from this coil_id (inclusive), for example 116494.",
    )
    return parser.parse_args()


def iter_gray_images(roots: Sequence[Path]) -> Iterable[tuple[Path, Path]]:
    for root in roots:
        if not root.exists():
            print(f"[skip] input not found: {root}")
            continue
        items = []
        for image_path in root.glob(r"*\jpg\GRAY.jpg"):
            if image_path.is_file():
                coil_id = get_coil_id(root, image_path)
                items.append((coil_id, image_path))
        items.sort(key=lambda item: coil_sort_key(item[0], str(item[1])))
        for _, image_path in items:
            yield root, image_path


def reserve_path(path: Path) -> Path:
    if not path.exists():
        return path
    index = 1
    while True:
        candidate = path.with_name(f"{path.stem}_{index}{path.suffix}")
        if not candidate.exists():
            return candidate
        index += 1


def save_pascal_voc_xml(path: Path, image_name: str, width: int, height: int, boxes: List[dict]) -> None:
    annotation = Element("annotation")
    SubElement(annotation, "folder").text = path.parent.name
    SubElement(annotation, "filename").text = image_name

    size = SubElement(annotation, "size")
    SubElement(size, "width").text = str(width)
    SubElement(size, "height").text = str(height)
    SubElement(size, "depth").text = "3"
    SubElement(annotation, "segmented").text = "0"

    for box in boxes:
        obj = SubElement(annotation, "object")
        SubElement(obj, "name").text = box["label"]
        SubElement(obj, "pose").text = "Unspecified"
        SubElement(obj, "truncated").text = "0"
        SubElement(obj, "difficult").text = "0"
        bndbox = SubElement(obj, "bndbox")
        xmin, ymin, xmax, ymax = [int(v) for v in box["bbox"]]
        SubElement(bndbox, "xmin").text = str(xmin)
        SubElement(bndbox, "ymin").text = str(ymin)
        SubElement(bndbox, "xmax").text = str(xmax)
        SubElement(bndbox, "ymax").text = str(ymax)

    path.parent.mkdir(parents=True, exist_ok=True)
    ElementTree(annotation).write(path, encoding="utf-8")


def tile_bounds(width: int, height: int, rows: int, cols: int) -> Iterable[tuple[int, int, int, int, int, int]]:
    tile_w = math.ceil(width / cols)
    tile_h = math.ceil(height / rows)
    for row in range(rows):
        top = row * tile_h
        bottom = min((row + 1) * tile_h, height)
        if top >= bottom:
            continue
        for col in range(cols):
            left = col * tile_w
            right = min((col + 1) * tile_w, width)
            if left >= right:
                continue
            yield row, col, left, top, right, bottom


def parse_detection_result(result) -> List[dict]:
    boxes = []
    for box in result.boxes:
        xyxy = box.xyxy[0].cpu().tolist()
        boxes.append(
            {
                "label": result.names.get(int(box.cls[0].item()), "defect"),
                "det_conf": float(box.conf[0].item()),
                "bbox": [xyxy[0], xyxy[1], xyxy[2], xyxy[3]],
            }
        )
    return boxes


def get_coil_id(source_root: Path, image_path: Path) -> str:
    relative_path = image_path.relative_to(source_root)
    return relative_path.parts[0] if relative_path.parts else image_path.parent.name


def coil_sort_key(coil_id: str, image_path: str) -> tuple[int, str, str]:
    if str(coil_id).isdigit():
        return 0, f"{int(coil_id):020d}", image_path
    return 1, str(coil_id), image_path


def get_source_tag(source_root: Path) -> str:
    name = source_root.name.upper()
    if name.endswith("_L"):
        return "L"
    if name.endswith("_S"):
        return "S"
    return name


def classify_boxes(tile: Image.Image, boxes: List[dict], classifier_model: CoilClsModel) -> List[dict]:
    if not boxes:
        return []

    crops = []
    valid_boxes = []
    for box in boxes:
        xmin, ymin, xmax, ymax = [int(v) for v in box["bbox"]]
        xmin = max(0, xmin)
        ymin = max(0, ymin)
        xmax = min(tile.width, xmax)
        ymax = min(tile.height, ymax)
        if xmin >= xmax or ymin >= ymax:
            continue
        crops.append(tile.crop((xmin, ymin, xmax, ymax)))
        valid_boxes.append(box)

    if not crops:
        return []

    cls_indices, cls_confs, _ = classifier_model.predict_image(crops, bach_size=32)
    for box, cls_index, cls_conf in zip(valid_boxes, cls_indices, cls_confs):
        if 0 <= int(cls_index) < len(CLASS_NAMES):
            box["label"] = CLASS_NAMES[int(cls_index)]
        else:
            box["label"] = CLASS_NAMES[0]
        box["cls_conf"] = float(cls_conf)
    return valid_boxes


def choose_tile_label(boxes: List[dict], class_names: Sequence[str]) -> str:
    if not boxes:
        return class_names[0]
    best_box = max(boxes, key=lambda item: float(item.get("cls_conf", 0.0)))
    label = best_box["label"]
    return label if label in class_names else class_names[0]


class RuntimeContext:
    def __init__(self, args: argparse.Namespace) -> None:
        from ultralytics import YOLO
        import torch

        torch.set_num_threads(max(1, args.cpu_threads))
        if hasattr(torch, "set_num_interop_threads"):
            torch.set_num_interop_threads(max(1, min(args.cpu_threads, 4)))

        self.det_model = YOLO(args.model)
        self.cls_model = CoilClsModel(config=args.classifier_config)
        self.class_names = list(CLASS_NAMES)
        self.gpu_lock = threading.Lock()
        self.counter_lock = threading.Lock()
        self.label_counters = {}


def process_image(
    source_root: Path,
    image_path: Path,
    output_root: Path,
    args: argparse.Namespace,
    runtime: RuntimeContext,
) -> dict:
    det_seconds = 0.0
    cls_seconds = 0.0
    saved_tiles = 0
    positive_tiles = 0

    try:
        with Image.open(image_path) as image:
            rgb_image = image.convert("RGB")
            width, height = rgb_image.size
            coil_id = get_coil_id(source_root, image_path)
            source_tag = get_source_tag(source_root)

            tile_records = []
            for row, col, left, top, right, bottom in tile_bounds(width, height, args.rows, args.cols):
                tile_records.append(
                    {
                        "row": row,
                        "col": col,
                        "tile": rgb_image.crop((left, top, right, bottom)),
                    }
                )

            det_start = time.perf_counter()
            with runtime.gpu_lock:
                det_results = runtime.det_model.predict(
                    [record["tile"] for record in tile_records],
                    conf=args.conf,
                    imgsz=args.imgsz,
                    verbose=False,
                )
            det_seconds += time.perf_counter() - det_start

            for record, det_result in zip(tile_records, det_results):
                boxes = parse_detection_result(det_result)
                if not boxes:
                    continue

                cls_start = time.perf_counter()
                with runtime.gpu_lock:
                    boxes = classify_boxes(record["tile"], boxes, runtime.cls_model)
                cls_seconds += time.perf_counter() - cls_start
                if not boxes:
                    continue

                positive_tiles += 1
                label_name = choose_tile_label(boxes, runtime.class_names)
                label_dir = output_root / label_name
                label_dir.mkdir(parents=True, exist_ok=True)

                file_stem = f"{coil_id}_{source_tag}_r{record['row']:02d}_c{record['col']:02d}"
                image_out = reserve_path(label_dir / f"{file_stem}.jpg")
                xml_out = image_out.with_suffix(".xml")

                record["tile"].save(image_out, quality=95)
                save_pascal_voc_xml(
                    xml_out,
                    image_out.name,
                    record["tile"].width,
                    record["tile"].height,
                    boxes,
                )
                saved_tiles += 1
    except Exception as exc:
        raise RuntimeError(f"{image_path}: {exc}") from exc

    return {
        "saved_tiles": saved_tiles,
        "positive_tiles": positive_tiles,
        "det_seconds": det_seconds,
        "cls_seconds": cls_seconds,
    }


def main() -> None:
    args = parse_args()
    runtime = RuntimeContext(args)

    input_roots = [Path(item) for item in args.inputs]
    output_root = Path(args.output)
    output_root.mkdir(parents=True, exist_ok=True)

    source_items = iter_gray_images(input_roots)
    if args.start_coil_id:
        source_items = (
            item for item in source_items
            if coil_sort_key(get_coil_id(item[0], item[1]), str(item[1]))
            >= coil_sort_key(args.start_coil_id, "")
        )
    if args.limit:
        source_items = itertools.islice(source_items, args.limit)

    processed_images = 0
    saved_tiles = 0
    positive_tiles = 0
    det_seconds = 0.0
    cls_seconds = 0.0
    start_time = time.perf_counter()
    max_workers = max(1, args.workers)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        pending = set()

        def submit_item(item: tuple[Path, Path]) -> None:
            source_root, image_path = item
            pending.add(executor.submit(process_image, source_root, image_path, output_root, args, runtime))

        for _ in range(max_workers):
            try:
                submit_item(next(source_items))
            except StopIteration:
                break

        while pending:
            done, pending = wait(pending, return_when=FIRST_COMPLETED)
            for future in done:
                should_submit_next = True
                try:
                    result = future.result()
                except Exception as exc:
                    print(f"[error] worker failed: {exc}")
                else:
                    processed_images += 1
                    saved_tiles += result["saved_tiles"]
                    positive_tiles += result["positive_tiles"]
                    det_seconds += result["det_seconds"]
                    cls_seconds += result["cls_seconds"]

                    if processed_images % 10 == 0:
                        avg_det = det_seconds / processed_images if processed_images else 0.0
                        avg_cls = cls_seconds / processed_images if processed_images else 0.0
                        print(
                            f"[progress] images={processed_images} saved_tiles={saved_tiles} "
                            f"positive_tiles={positive_tiles} avg_det_s={avg_det:.3f} avg_cls_s={avg_cls:.3f}"
                        )

                if should_submit_next:
                    try:
                        submit_item(next(source_items))
                    except StopIteration:
                        pass

    elapsed = time.perf_counter() - start_time
    avg_det = det_seconds / processed_images if processed_images else 0.0
    avg_cls = cls_seconds / processed_images if processed_images else 0.0
    avg_total = elapsed / processed_images if processed_images else 0.0
    images_per_min = (processed_images / elapsed * 60.0) if elapsed > 0 else 0.0
    print(
        f"[done] images={processed_images} saved_tiles={saved_tiles} positive_tiles={positive_tiles} "
        f"det_s={det_seconds:.3f} cls_s={cls_seconds:.3f} total_s={elapsed:.3f} "
        f"avg_det_s={avg_det:.3f} avg_cls_s={avg_cls:.3f} avg_total_s={avg_total:.3f} "
        f"images_per_min={images_per_min:.2f} workers={max_workers} output={output_root}"
    )


if __name__ == "__main__":
    main()
