import argparse
import sys
from pathlib import Path

from PIL import Image


ROOT_DIR = Path(__file__).resolve().parents[1]
APP_DIR = ROOT_DIR / "app"
BASE_DIR = APP_DIR / "Base"
ALGO_RUNTIME_DIR = APP_DIR / "algorithm_runtime"
for path in (str(ROOT_DIR), str(APP_DIR), str(BASE_DIR), str(ALGO_RUNTIME_DIR)):
    if path not in sys.path:
        sys.path.insert(0, path)

import Globs
from Base.alg import detection
from Base.alg.tool import create_xml


DEFAULT_OUTPUT_ROOT = Path(r"D:\检出优化\20260321_折叠检出")
SOURCE_ROOTS = [Path(r"D:\Save_S"), Path(r"E:\Save_L")]
CLIP_NUM = 10


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export detection tiles and xml from Save_S/Save_L.")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--limit", type=int, default=0, help="Limit processed coils per source root, 0 means no limit.")
    parser.add_argument("--skip-existing", action="store_true", help="Skip coils already recorded in progress file.")
    return parser.parse_args()


def iter_coil_dirs(root: Path):
    for coil_dir in sorted(root.iterdir()):
        if coil_dir.is_dir():
            yield coil_dir


def build_progress_set(progress_file: Path) -> set[str]:
    if not progress_file.exists():
        return set()
    processed = set()
    for line in progress_file.read_text(encoding="utf-8", errors="ignore").splitlines():
        if line.strip():
            processed.add(line.strip())
    return processed


def save_progress(progress_file: Path, coil_key: str) -> None:
    progress_file.parent.mkdir(parents=True, exist_ok=True)
    with progress_file.open("a", encoding="utf-8") as f:
        f.write(f"{coil_key}\n")


def choose_folder_name(labels: list[str]) -> str:
    if not labels:
        return "empty"
    if "折叠" in labels:
        return "折叠"
    unique_labels = sorted(set(labels))
    if len(unique_labels) == 1:
        return unique_labels[0]
    return "mixed"


def export_detection_tiles(coil_dir: Path, output_root: Path, source_tag: str) -> tuple[int, int]:
    gray_path = coil_dir / "jpg" / "GRAY.jpg"
    mask_path = coil_dir / "mask" / "MASK.png"
    if not gray_path.exists() or not mask_path.exists():
        return 0, 0

    with Image.open(gray_path) as gray_image, Image.open(mask_path) as mask_image:
        pil_gray = gray_image.convert("RGB")
        pil_mask = mask_image.convert("L")
        res_list, clip_image_list, clip_info_list = detection.detection_by_image(
            pil_gray,
            pil_mask,
            clip_num=CLIP_NUM,
            save_base_folder=None,
            save_only=False,
        )

    exported_tiles = 0
    fold_hits = 0
    for clip_index, (clip_res, clip_image, clip_info) in enumerate(
        zip(res_list, clip_image_list, clip_info_list), start=1
    ):
        if not clip_res:
            continue

        x_offset, y_offset, *_ = clip_info
        xml_boxes = []
        labels = []
        for xmin, ymin, xmax, ymax, label_index, source, name in clip_res:
            label_name = str(name)
            labels.append(label_name)
            if label_name == "折叠":
                fold_hits += 1
            xml_boxes.append(
                (
                    max(int(xmin - x_offset), 0),
                    max(int(ymin - y_offset), 0),
                    max(int(xmax - x_offset), 1),
                    max(int(ymax - y_offset), 1),
                    label_index,
                    source,
                    label_name,
                )
            )

        folder_name = choose_folder_name(labels)
        target_dir = output_root / folder_name
        target_dir.mkdir(parents=True, exist_ok=True)

        file_stem = f"{coil_dir.name}_{source_tag}_{clip_index}"
        image_path = target_dir / f"{file_stem}.png"
        clip_image.save(image_path)
        create_xml(image_path, [clip_image.height, clip_image.width, 3], xml_boxes, output_folder=target_dir)
        exported_tiles += 1

    return exported_tiles, fold_hits


def main() -> None:
    args = parse_args()
    output_root = args.output_root
    output_root.mkdir(parents=True, exist_ok=True)
    progress_file = output_root / "processed_coils.txt"
    processed_coils = build_progress_set(progress_file) if args.skip_existing else set()

    Globs.control.save_detection = False
    Globs.control.save_sub_image = False

    total_coils = 0
    total_tiles = 0
    total_fold_hits = 0

    for source_root in SOURCE_ROOTS:
        source_tag = "S" if source_root.drive.upper().startswith("D:") else "L"
        processed_in_root = 0
        for coil_dir in iter_coil_dirs(source_root):
            coil_key = f"{source_root}:{coil_dir.name}"
            if coil_key in processed_coils:
                continue
            if args.limit and processed_in_root >= args.limit:
                break

            try:
                tile_count, fold_hits = export_detection_tiles(coil_dir, output_root, source_tag)
                total_coils += 1
                processed_in_root += 1
                total_tiles += tile_count
                total_fold_hits += fold_hits
                save_progress(progress_file, coil_key)
                print(
                    f"[ok] coil={coil_dir.name} source={source_tag} "
                    f"tiles={tile_count} fold_hits={fold_hits}"
                )
            except Exception as e:
                print(f"[error] coil={coil_dir} error={e}")

    print(
        f"[done] coils={total_coils} tiles={total_tiles} "
        f"fold_hits={total_fold_hits} output={output_root}"
    )


if __name__ == "__main__":
    main()
