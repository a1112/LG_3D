import argparse
import json
import re
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Optional

from PIL import Image, UnidentifiedImageError

ROOT_DIR = Path(__file__).resolve().parents[1]
APP_DIR = ROOT_DIR / "app"
DB_PACKAGE_DIR = ROOT_DIR / "package" / "CoilDataBase"
DEFAULT_OUTPUT_DIR = Path(r"D:\检出优化\2D收集")
DEFAULT_AREA_CONFIG = Path(r"D:\CONFIG_3D\configs\area_join.json")
FALLBACK_AREA_CONFIG = ROOT_DIR / "app" / "algorithm_runtime_2D" / "config" / "area_join.json"

for import_path in (APP_DIR, DB_PACKAGE_DIR):
    path_text = str(import_path)
    if path_text not in sys.path:
        sys.path.insert(0, path_text)

Image.MAX_IMAGE_PIXELS = None


@dataclass
class DefectRecord:
    defect_id: int
    coil_id: int
    surface: str
    defect_name: str
    defect_x: int
    defect_y: int
    defect_w: int
    defect_h: int
    defect_source: Optional[float]


@dataclass
class CropResult:
    defect_id: int
    coil_id: int
    surface: str
    defect_name: str
    gray_path: str
    area_path: str
    save_path: str
    gray_size: tuple[int, int]
    area_size: tuple[int, int]
    gray_center: tuple[float, float]
    area_center: tuple[int, int]
    crop_box: tuple[int, int, int, int]
    defect_box: tuple[int, int, int, int]
    defect_source: Optional[float]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="按 3D 缺陷坐标比例映射到 2D AREA 图，并裁剪 1024x1024 样本。")
    parser.add_argument("--output",
                        type=Path,
                        default=DEFAULT_OUTPUT_DIR,
                        help="输出目录，默认 D:\\检出优化\\2D收集")
    parser.add_argument("--area-config",
                        type=Path,
                        default=DEFAULT_AREA_CONFIG,
                        help="2D AREA 拼接配置 area_join.json")
    parser.add_argument("--size", type=int, default=1024, help="裁剪尺寸，默认 1024")
    parser.add_argument("--defect-name",
                        action="append",
                        default=[],
                        help="只收集指定缺陷名；可重复传入，例如 --defect-name 毛刺")
    parser.add_argument("--surface",
                        action="append",
                        choices=["S", "L"],
                        default=[],
                        help="只收集指定面；可重复传入")
    parser.add_argument("--coil-id",
                        action="append",
                        type=int,
                        default=[],
                        help="只收集指定卷号；可重复传入")
    parser.add_argument("--start-coil-id", type=int, default=None, help="起始卷号")
    parser.add_argument("--end-coil-id", type=int, default=None, help="结束卷号")
    parser.add_argument("--limit", type=int, default=None, help="最多处理多少条缺陷")
    parser.add_argument("--include-2d",
                        action="store_true",
                        help="默认排除 2D_ 缺陷；传入后包含 2D_ 缺陷")
    parser.add_argument("--flip-x", action="store_true", help="映射到 AREA 后左右翻转")
    parser.add_argument("--flip-y", action="store_true", help="映射到 AREA 后上下翻转")
    parser.add_argument("--dry-run", action="store_true", help="只统计和打印，不保存图片")
    return parser.parse_args()


def load_area_save_folders(config_path: Path) -> dict[str, Path]:
    if not config_path.exists():
        config_path = FALLBACK_AREA_CONFIG
    with config_path.open("r", encoding="utf-8") as f:
        config = json.load(f)

    surfaces = config.get("surfaces", {})
    return {
        surface_key: Path(surface_config["save_folder"])
        for surface_key, surface_config in surfaces.items()
        if "save_folder" in surface_config
    }


def image_path_with_existing_suffix(path: Path) -> Optional[Path]:
    if path.exists() and path.is_file() and path.stat().st_size > 0:
        return path
    for suffix in (".jpg", ".jpeg", ".png", ".bmp"):
        candidate = path.with_suffix(suffix)
        if candidate.exists() and candidate.is_file() and candidate.stat(
        ).st_size > 0:
            return candidate
    return None


def get_area_path(area_save_folders: dict[str, Path], coil_id: int,
                  surface: str) -> Optional[Path]:
    save_folder = area_save_folders.get(surface)
    if save_folder is None:
        return None

    candidates = (
        save_folder / str(coil_id) / "jpg" / "AREA.jpg",
        save_folder / str(coil_id) / "preview" / "AREA.jpg",
    )
    for candidate in candidates:
        existing = image_path_with_existing_suffix(candidate)
        if existing is not None:
            return existing
    return None


def load_server_config() -> None:
    import Base.CONFIG  # noqa: F401


def get_gray_path(coil_id: int, surface: str) -> Optional[Path]:
    from Base.CONFIG import serverConfigProperty

    configured_path = Path(
        serverConfigProperty.get_file(coil_id, surface, "GRAY"))
    for image_type in ("GRAY", "JET", "MASK"):
        candidate = image_path_with_existing_suffix(
            configured_path.with_name(image_type + configured_path.suffix))
        if candidate is not None:
            return candidate
    return None


def query_defects(args: argparse.Namespace) -> list[DefectRecord]:
    from CoilDataBase.core import Session
    from CoilDataBase.models import CoilDefect

    with Session() as session:
        query = session.query(CoilDefect)
        if not args.include_2d:
            query = query.filter(
                ~CoilDefect.defectName.like("2D\\_%", escape="\\"))
        if args.defect_name:
            query = query.filter(CoilDefect.defectName.in_(args.defect_name))
        if args.surface:
            query = query.filter(CoilDefect.surface.in_(args.surface))
        if args.coil_id:
            query = query.filter(CoilDefect.secondaryCoilId.in_(args.coil_id))
        if args.start_coil_id is not None:
            query = query.filter(
                CoilDefect.secondaryCoilId >= args.start_coil_id)
        if args.end_coil_id is not None:
            query = query.filter(
                CoilDefect.secondaryCoilId <= args.end_coil_id)

        query = query.order_by(CoilDefect.secondaryCoilId.asc(),
                               CoilDefect.Id.asc())
        if args.limit:
            query = query.limit(args.limit)

        return [
            DefectRecord(
                defect_id=int(defect.Id),
                coil_id=int(defect.secondaryCoilId),
                surface=str(defect.surface),
                defect_name=str(defect.defectName),
                defect_x=int(defect.defectX or 0),
                defect_y=int(defect.defectY or 0),
                defect_w=max(1, int(defect.defectW or 1)),
                defect_h=max(1, int(defect.defectH or 1)),
                defect_source=defect.defectSource,
            ) for defect in query.all()
        ]


def safe_path_name(value: str) -> str:
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value)
    value = value.strip().strip(".")
    return value or "unknown"


def clamp(value: int, min_value: int, max_value: int) -> int:
    return max(min_value, min(value, max_value))


def fill_value_for_mode(mode: str):
    if mode in {"1", "L", "I", "F", "P"}:
        return 0
    if mode == "RGBA":
        return (0, 0, 0, 255)
    if mode == "LA":
        return (0, 255)
    return (0, 0, 0)


def center_crop_with_padding(
        image: Image.Image, center_x: int, center_y: int,
        size: int) -> tuple[Image.Image, tuple[int, int, int, int]]:
    image_w, image_h = image.size
    center_x = clamp(center_x, 0, max(0, image_w - 1))
    center_y = clamp(center_y, 0, max(0, image_h - 1))

    left = int(round(center_x - size / 2))
    top = int(round(center_y - size / 2))
    right = left + size
    bottom = top + size

    source_left = clamp(left, 0, image_w)
    source_top = clamp(top, 0, image_h)
    source_right = clamp(right, 0, image_w)
    source_bottom = clamp(bottom, 0, image_h)

    crop = image.crop((source_left, source_top, source_right, source_bottom))
    if crop.size == (size, size):
        return crop, (left, top, right, bottom)

    padded = Image.new(image.mode, (size, size),
                       fill_value_for_mode(image.mode))
    paste_x = source_left - left
    paste_y = source_top - top
    padded.paste(crop, (paste_x, paste_y))
    return padded, (left, top, right, bottom)


def map_gray_center_to_area(
        defect: DefectRecord,
        gray_size: tuple[int, int],
        area_size: tuple[int, int],
        flip_x: bool = False,
        flip_y: bool = False) -> tuple[tuple[float, float], tuple[int, int]]:
    gray_w, gray_h = gray_size
    area_w, area_h = area_size
    gray_center_x = defect.defect_x + defect.defect_w / 2
    gray_center_y = defect.defect_y + defect.defect_h / 2
    area_center_x = int(round(gray_center_x / gray_w * area_w))
    area_center_y = int(round(gray_center_y / gray_h * area_h))
    if flip_x:
        area_center_x = area_w - 1 - area_center_x
    if flip_y:
        area_center_y = area_h - 1 - area_center_y
    return (gray_center_x, gray_center_y), (area_center_x, area_center_y)


def iter_grouped_defects(defects: Iterable[DefectRecord]):
    grouped = defaultdict(list)
    for defect in defects:
        grouped[(defect.coil_id, defect.surface)].append(defect)
    for key in sorted(grouped):
        yield key, grouped[key]


def save_metadata(metadata_path: Path, result: CropResult) -> None:
    with metadata_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(result), ensure_ascii=False) + "\n")


def open_image_pair(
        gray_path: Path, area_path: Path
) -> tuple[Optional[Image.Image], Optional[Image.Image]]:
    try:
        gray_image = Image.open(gray_path)
        gray_image.load()
        area_image = Image.open(area_path)
        area_image.load()
        return gray_image, area_image
    except (OSError, UnidentifiedImageError) as e:
        print(f"跳过无效图片: GRAY={gray_path}, AREA={area_path}, error={e}")
        return None, None


def collect(args: argparse.Namespace) -> tuple[int, int]:
    load_server_config()
    area_save_folders = load_area_save_folders(args.area_config)
    defects = query_defects(args)
    output_dir = args.output
    metadata_path = output_dir / "metadata.jsonl"

    print(f"待处理缺陷数: {len(defects)}")
    print(f"输出目录: {output_dir}")
    print(f"AREA 配置面: {', '.join(sorted(area_save_folders))}")

    saved_count = 0
    skipped_count = 0

    if not args.dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)

    for (coil_id, surface), group in iter_grouped_defects(defects):
        gray_path = get_gray_path(coil_id, surface)
        area_path = get_area_path(area_save_folders, coil_id, surface)
        if gray_path is None or area_path is None:
            skipped_count += len(group)
            print(
                f"跳过 coil={coil_id} surface={surface}: GRAY={gray_path}, AREA={area_path}"
            )
            continue

        gray_image, area_image = open_image_pair(gray_path, area_path)
        if gray_image is None or area_image is None:
            skipped_count += len(group)
            continue

        with gray_image, area_image:
            gray_size = gray_image.size
            area_size = area_image.size

            for defect in group:
                gray_center, area_center = map_gray_center_to_area(
                    defect,
                    gray_size,
                    area_size,
                    flip_x=args.flip_x,
                    flip_y=args.flip_y,
                )
                crop_image, crop_box = center_crop_with_padding(
                    area_image,
                    area_center[0],
                    area_center[1],
                    args.size,
                )

                class_dir = output_dir / safe_path_name(
                    defect.defect_name) / surface
                file_name = (
                    f"{defect.coil_id}_{surface}_defect{defect.defect_id}_"
                    f"area_{area_center[0]}_{area_center[1]}_size{args.size}.jpg"
                )
                save_path = class_dir / file_name

                result = CropResult(
                    defect_id=defect.defect_id,
                    coil_id=defect.coil_id,
                    surface=defect.surface,
                    defect_name=defect.defect_name,
                    gray_path=str(gray_path),
                    area_path=str(area_path),
                    save_path=str(save_path),
                    gray_size=gray_size,
                    area_size=area_size,
                    gray_center=gray_center,
                    area_center=area_center,
                    crop_box=crop_box,
                    defect_box=(defect.defect_x, defect.defect_y,
                                defect.defect_w, defect.defect_h),
                    defect_source=defect.defect_source,
                )

                if not args.dry_run:
                    class_dir.mkdir(parents=True, exist_ok=True)
                    crop_image.save(save_path, quality=95)
                    save_metadata(metadata_path, result)
                saved_count += 1

    return saved_count, skipped_count


def main() -> None:
    args = parse_args()
    saved_count, skipped_count = collect(args)
    action = "可保存" if args.dry_run else "已保存"
    print(f"{action}: {saved_count}, 跳过: {skipped_count}")


if __name__ == "__main__":
    main()
