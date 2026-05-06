import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import time
from dataclasses import asdict, dataclass
from multiprocessing import Process
from pathlib import Path
from typing import Iterable, Sequence
from xml.etree.ElementTree import Element, ElementTree, SubElement

ROOT_DIR = Path(__file__).resolve().parents[1]
ALG_2D_DIR = ROOT_DIR / "app" / "algorithm_runtime_2D"
DEFAULT_INPUT_DIR = Path(r"D:\检出优化\2D检出\2D收集")
DEFAULT_OUTPUT_DIR = Path(r"D:\检出优化\2D检出\out")
DEFAULT_MODEL = Path(r"D:\CONFIG_3D\model\CoilDetection_Area_JC.pt")

if str(ALG_2D_DIR) not in sys.path:
    sys.path.insert(0, str(ALG_2D_DIR))

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp"}
SURFACE_NAMES = {"S", "L", "R"}


@dataclass
class DetectionBox:
    label: str
    confidence: float
    bbox: tuple[int, int, int, int]


@dataclass
class MovedDetection:
    source_path: str
    image_path: str
    xml_path: str
    detections: list[dict]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Recursively run CoilDetection_Area_JC.pt and move detected 2D tiles to an output folder."
    )
    parser.add_argument(
        "--input",
        dest="inputs",
        action="append",
        type=Path,
        default=None,
        help="Input folder scanned recursively. Can be passed multiple times.",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_DIR, help="Output folder for detected images.")
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL, help="YOLO detection model path.")
    parser.add_argument("--workers", type=int, default=4, help="Number of worker processes.")
    parser.add_argument("--batch-size", type=int, default=32, help="YOLO predict batch size per worker.")
    parser.add_argument("--conf", type=float, default=0.25, help="Detection confidence threshold.")
    parser.add_argument("--imgsz", type=int, default=1024, help="YOLO inference image size.")
    parser.add_argument("--device", default="", help="YOLO device, for example 0 or cpu. Empty means automatic.")
    parser.add_argument("--half", action="store_true", help="Use FP16 inference when supported by the selected device.")
    parser.add_argument("--limit", type=int, default=0, help="Max images to scan from the manifest. 0 means no limit.")
    parser.add_argument("--copy", action="store_true", help="Copy detected images instead of moving them.")
    parser.add_argument("--dry-run", action="store_true", help="Run detection without moving images or writing XML files.")
    parser.add_argument(
        "--include-output",
        action="store_true",
        help="Do not skip images under the output folder when an input contains the output folder.",
    )
    parser.add_argument(
        "--progress-seconds",
        type=float,
        default=60.0,
        help="Seconds between progress log lines in each worker.",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help="Optional manifest path. Defaults to output/detection_manifest.txt.",
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        default=None,
        help="Optional metadata jsonl path. Defaults to output/metadata.jsonl.",
    )
    return parser.parse_args()


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def iter_images(input_dirs: Sequence[Path], output_dir: Path, include_output: bool) -> Iterable[Path]:
    resolved_output = output_dir.resolve()
    for input_dir in input_dirs:
        resolved_input = input_dir.resolve()
        output_inside_input = is_relative_to(resolved_output, resolved_input)
        for path in input_dir.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix.lower() not in IMAGE_SUFFIXES:
                continue
            if not include_output and output_inside_input and is_relative_to(path.resolve(), resolved_output):
                continue
            yield path


def write_manifest(input_dirs: Sequence[Path], output_dir: Path, manifest_path: Path, limit: int,
                   include_output: bool) -> int:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    seen_paths = set()
    with manifest_path.open("w", encoding="utf-8", newline="\n") as f:
        for image_path in iter_images(input_dirs, output_dir, include_output):
            resolved_path = str(image_path.resolve())
            if resolved_path in seen_paths:
                continue
            seen_paths.add(resolved_path)
            f.write(str(image_path) + "\n")
            count += 1
            if limit and count >= limit:
                break
    return count


def load_model(model_path: Path):
    from ultralytics import YOLO

    return YOLO(str(model_path))


def normalize_label(label: str) -> str:
    try:
        fixed_label = label.encode("gbk").decode("utf-8")
    except UnicodeError:
        return label
    return fixed_label or label


def parse_detection_result(result) -> tuple[int, int, list[DetectionBox]]:
    height, width = result.orig_shape[:2]
    names = result.names
    detections = []
    for box in result.boxes:
        xyxy = box.xyxy[0].cpu().tolist()
        cls_index = int(box.cls[0].item())
        label = normalize_label(str(names.get(cls_index, cls_index)))
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
    return width, height, detections


def predict_paths(model, batch: Sequence[Path], args: dict):
    kwargs = {
        "conf": args["conf"],
        "imgsz": args["imgsz"],
        "verbose": False,
    }
    if args["device"]:
        kwargs["device"] = args["device"]
    if args["half"]:
        kwargs["half"] = True
    return model.predict([str(path) for path in batch], **kwargs)


def safe_path_name(value: str) -> str:
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value)
    value = value.strip().strip(".")
    return value or "unknown"


def parse_coil_surface(path: Path) -> tuple[str, str]:
    match = re.match(r"^(?P<coil>\d+)[_-](?P<surface>[A-Za-z])[_-]", path.stem)
    if match:
        return match.group("coil"), match.group("surface").upper()

    coil_id = "unknown"
    surface = "unknown"
    for part in reversed(path.parts):
        if part.upper() in SURFACE_NAMES:
            surface = part.upper()
        if part.isdigit():
            coil_id = part
            break
    return coil_id, surface


def coil_bucket(coil_id: str, bucket_size: int = 10000) -> str:
    if not coil_id.isdigit():
        return "unknown"
    return str(int(coil_id) // bucket_size * bucket_size)


def destination_for(output_dir: Path, source_path: Path) -> Path:
    coil_id, surface = parse_coil_surface(source_path)
    return output_dir / coil_bucket(coil_id) / safe_path_name(surface) / source_path.name


def path_digest(path: Path) -> str:
    return hashlib.sha1(str(path).encode("utf-8", errors="replace")).hexdigest()[:10]


def reserve_path(path: Path) -> tuple[Path, Path]:
    path.parent.mkdir(parents=True, exist_ok=True)
    for index in range(100000):
        if index == 0:
            candidate = path
        elif index == 1:
            candidate = path.with_name(f"{path.stem}_{path_digest(path)}{path.suffix}")
        else:
            candidate = path.with_name(f"{path.stem}_{index - 1}{path.suffix}")
        lock_path = candidate.with_suffix(candidate.suffix + ".lock")
        if candidate.exists():
            continue
        try:
            lock_handle = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            continue
        os.close(lock_handle)
        return candidate, lock_path
    raise RuntimeError(f"cannot reserve output path: {path}")


def save_pascal_voc_xml(path: Path, image_path: Path, width: int, height: int,
                        detections: Sequence[DetectionBox]) -> None:
    annotation = Element("annotation")
    SubElement(annotation, "folder").text = image_path.parent.name
    SubElement(annotation, "filename").text = image_path.name
    SubElement(annotation, "path").text = str(image_path)

    size = SubElement(annotation, "size")
    SubElement(size, "width").text = str(width)
    SubElement(size, "height").text = str(height)
    SubElement(size, "depth").text = "3"
    SubElement(annotation, "segmented").text = "0"

    for detection in detections:
        obj = SubElement(annotation, "object")
        SubElement(obj, "name").text = detection.label
        SubElement(obj, "pose").text = "Unspecified"
        SubElement(obj, "truncated").text = "0"
        SubElement(obj, "difficult").text = "0"
        SubElement(obj, "confidence").text = f"{detection.confidence:.6f}"
        bndbox = SubElement(obj, "bndbox")
        xmin, ymin, xmax, ymax = detection.bbox
        SubElement(bndbox, "xmin").text = str(xmin)
        SubElement(bndbox, "ymin").text = str(ymin)
        SubElement(bndbox, "xmax").text = str(xmax)
        SubElement(bndbox, "ymax").text = str(ymax)

    ElementTree(annotation).write(path, encoding="utf-8", xml_declaration=True)


def append_metadata(metadata_path: Path, moved_detection: MovedDetection) -> None:
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    with metadata_path.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(asdict(moved_detection), ensure_ascii=False) + "\n")


def should_keep_in_output(source_path: Path, output_dir: Path) -> bool:
    return is_relative_to(source_path.resolve(), output_dir.resolve())


def move_detection(source_path: Path, output_dir: Path, metadata_path: Path, width: int, height: int,
                   detections: Sequence[DetectionBox], copy_mode: bool, dry_run: bool) -> MovedDetection:
    if should_keep_in_output(source_path, output_dir):
        target_path = source_path
        xml_path = target_path.with_suffix(".xml")
        if not dry_run:
            save_pascal_voc_xml(xml_path, target_path, width, height, detections)
        moved_detection = MovedDetection(
            source_path=str(source_path),
            image_path=str(target_path),
            xml_path=str(xml_path),
            detections=[asdict(detection) for detection in detections],
        )
        if not dry_run:
            append_metadata(metadata_path, moved_detection)
        return moved_detection

    target_path, lock_path = reserve_path(destination_for(output_dir, source_path))
    xml_path = target_path.with_suffix(".xml")
    source_xml = source_path.with_suffix(".xml")

    try:
        if not dry_run:
            if copy_mode:
                shutil.copy2(source_path, target_path)
            else:
                shutil.move(str(source_path), target_path)
            save_pascal_voc_xml(xml_path, target_path, width, height, detections)
            if not copy_mode and source_xml.exists() and source_xml.resolve() != xml_path.resolve():
                source_xml.unlink()
    finally:
        if lock_path.exists():
            lock_path.unlink()

    moved_detection = MovedDetection(
        source_path=str(source_path),
        image_path=str(target_path),
        xml_path=str(xml_path),
        detections=[asdict(detection) for detection in detections],
    )
    if not dry_run:
        append_metadata(metadata_path, moved_detection)
    return moved_detection


def iter_worker_paths(manifest_path: Path, worker_id: int, workers: int) -> Iterable[Path]:
    with manifest_path.open("r", encoding="utf-8") as f:
        for index, line in enumerate(f):
            if index % workers == worker_id:
                value = line.strip()
                if value:
                    yield Path(value)


def worker_log(log_path: Path, message: str) -> None:
    with log_path.open("a", encoding="utf-8", newline="\n") as f:
        f.write(message + "\n")


def process_batch(model, batch: Sequence[Path], args: dict, stats: dict, log_path: Path) -> None:
    existing_batch = [path for path in batch if path.exists()]
    if not existing_batch:
        return

    try:
        results = predict_paths(model, existing_batch, args)
    except Exception as exc:
        if len(existing_batch) == 1:
            stats["errors"] += 1
            worker_log(log_path, f"ERROR image={existing_batch[0]} error={exc}")
            return
        for image_path in existing_batch:
            process_batch(model, [image_path], args, stats, log_path)
        return

    for image_path, result in zip(existing_batch, results):
        stats["processed"] += 1
        try:
            width, height, detections = parse_detection_result(result)
            if detections:
                move_detection(
                    image_path,
                    args["output"],
                    args["metadata"],
                    width,
                    height,
                    detections,
                    args["copy"],
                    args["dry_run"],
                )
                stats["detected_images"] += 1
                stats["boxes"] += len(detections)
        except Exception as exc:
            stats["errors"] += 1
            worker_log(log_path, f"ERROR image={image_path} error={exc}")


def worker_main(worker_id: int, args: dict) -> None:
    log_path = args["log_dir"] / f"out_detection_worker_{worker_id}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text("", encoding="utf-8")
    start_time = time.monotonic()
    stats = {
        "processed": 0,
        "detected_images": 0,
        "boxes": 0,
        "errors": 0,
    }

    model = load_model(args["model"])
    model_names = {key: normalize_label(str(value)) for key, value in model.names.items()}
    worker_log(log_path, f"START worker={worker_id} model={args['model']}")
    worker_log(log_path, f"MODEL names={model_names}")

    batch = []
    next_progress = time.monotonic() + args["progress_seconds"]
    for image_path in iter_worker_paths(args["manifest"], worker_id, args["workers"]):
        batch.append(image_path)
        if len(batch) >= args["batch_size"]:
            process_batch(model, batch, args, stats, log_path)
            batch = []

        now = time.monotonic()
        if now >= next_progress:
            elapsed = now - start_time
            rate = stats["processed"] / elapsed if elapsed > 0 else 0.0
            worker_log(
                log_path,
                "PROGRESS worker={worker} processed={processed} detected_images={detected_images} "
                "boxes={boxes} errors={errors} elapsed_sec={elapsed:.1f} rate={rate:.2f}/s".format(
                    worker=worker_id,
                    processed=stats["processed"],
                    detected_images=stats["detected_images"],
                    boxes=stats["boxes"],
                    errors=stats["errors"],
                    elapsed=elapsed,
                    rate=rate,
                ),
            )
            next_progress = now + args["progress_seconds"]

    if batch:
        process_batch(model, batch, args, stats, log_path)

    elapsed = time.monotonic() - start_time
    worker_log(
        log_path,
        "DONE worker={worker} processed={processed} detected_images={detected_images} "
        "boxes={boxes} errors={errors} elapsed_sec={elapsed:.1f}".format(
            worker=worker_id,
            processed=stats["processed"],
            detected_images=stats["detected_images"],
            boxes=stats["boxes"],
            errors=stats["errors"],
            elapsed=elapsed,
        ),
    )


def main() -> None:
    args = parse_args()
    input_dirs = [path.resolve() for path in (args.inputs or [DEFAULT_INPUT_DIR])]
    output_dir = args.output.resolve()
    manifest_path = (args.manifest or output_dir / "detection_manifest.txt").resolve()
    metadata_path = (args.metadata or output_dir / "metadata.jsonl").resolve()
    log_dir = output_dir

    for input_dir in input_dirs:
        if not input_dir.exists():
            raise FileNotFoundError(f"input folder not found: {input_dir}")
    if not args.model.exists():
        raise FileNotFoundError(f"model not found: {args.model}")

    output_dir.mkdir(parents=True, exist_ok=True)
    total_images = write_manifest(input_dirs, output_dir, manifest_path, args.limit, args.include_output)
    if total_images == 0:
        print(f"FOUND images=0 inputs={';'.join(str(path) for path in input_dirs)}")
        return

    runtime_args = {
        "inputs": input_dirs,
        "output": output_dir,
        "model": args.model.resolve(),
        "workers": max(1, args.workers),
        "batch_size": max(1, args.batch_size),
        "conf": args.conf,
        "imgsz": args.imgsz,
        "device": args.device,
        "half": args.half,
        "copy": args.copy,
        "dry_run": args.dry_run,
        "progress_seconds": max(1.0, args.progress_seconds),
        "manifest": manifest_path,
        "metadata": metadata_path,
        "log_dir": log_dir,
    }

    action = "copy" if args.copy else "move"
    if args.dry_run:
        action = f"dry-run {action}"
    print(
        f"START inputs={';'.join(str(path) for path in input_dirs)} "
        f"output={output_dir} model={args.model.resolve()} action={action}"
    )
    print(f"FOUND images={total_images}")
    print(f"MANIFEST path={manifest_path}")

    workers = []
    for worker_id in range(runtime_args["workers"]):
        process = Process(target=worker_main, args=(worker_id, runtime_args), daemon=False)
        process.start()
        workers.append(process)

    exit_codes = []
    for process in workers:
        process.join()
        exit_codes.append(process.exitcode)

    print(f"DONE workers={runtime_args['workers']} exit_codes={exit_codes}")
    if any(exit_code != 0 for exit_code in exit_codes):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
