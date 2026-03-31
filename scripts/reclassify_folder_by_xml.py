import argparse
import shutil
import sys
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET

from PIL import Image


ROOT_DIR = Path(__file__).resolve().parents[1]
APP_DIR = ROOT_DIR / "app"
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from Base.alg.CoilClsModel import CoilClsModel


IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png", ".bmp")
DEFAULT_ROOT = Path(r"D:\检出优化\0313")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Reclassify image+xml pairs into folders using XML crops.")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="Root folder containing class subfolders.")
    parser.add_argument(
        "--classifier-config",
        type=Path,
        default=Path(r"D:\CONFIG_3D\model\classifier\classifier.json"),
        help="Classifier config path.",
    )
    parser.add_argument("--batch-size", type=int, default=32, help="Classifier batch size.")
    parser.add_argument("--copy", action="store_true", help="Copy files instead of moving them.")
    return parser.parse_args()


def iter_xml_files(root: Path) -> Iterable[Path]:
    for xml_path in sorted(root.rglob("*.xml")):
        if xml_path.parent == root:
            continue
        yield xml_path


def find_image_for_xml(xml_path: Path) -> Path | None:
    for suffix in IMAGE_SUFFIXES:
        image_path = xml_path.with_suffix(suffix)
        if image_path.exists():
            return image_path
    return None


def safe_target_path(path: Path) -> Path:
    if not path.exists():
        return path
    index = 1
    while True:
        candidate = path.with_name(f"{path.stem}_{index}{path.suffix}")
        if not candidate.exists():
            return candidate
        index += 1


def extract_crops(image: Image.Image, xml_root: ET.Element) -> tuple[list[Image.Image], list[ET.Element]]:
    crops: list[Image.Image] = []
    objects: list[ET.Element] = []
    for obj in xml_root.findall("object"):
        bbox = obj.find("bndbox")
        if bbox is None:
            continue
        try:
            xmin = max(0, int(float(bbox.findtext("xmin", "0"))))
            ymin = max(0, int(float(bbox.findtext("ymin", "0"))))
            xmax = min(image.width, int(float(bbox.findtext("xmax", "0"))))
            ymax = min(image.height, int(float(bbox.findtext("ymax", "0"))))
        except Exception:
            continue
        if xmin >= xmax or ymin >= ymax:
            continue
        crops.append(image.crop((xmin, ymin, xmax, ymax)))
        objects.append(obj)
    return crops, objects


def predict_label(model: CoilClsModel, image_path: Path, xml_path: Path, batch_size: int) -> tuple[str, ET.ElementTree]:
    tree = ET.parse(xml_path)
    xml_root = tree.getroot()

    with Image.open(image_path) as image:
        rgb_image = image.convert("RGB")
        crops, objects = extract_crops(rgb_image, xml_root)

    if not crops:
        label = model.names[0] if model.names else "背景"
    else:
        cls_indices, cls_scores, cls_names = model.predict_image(crops, bach_size=batch_size)
        if not cls_indices:
            label = model.names[0] if model.names else "背景"
        else:
            best_pos = max(range(len(cls_indices)), key=lambda idx: float(cls_scores[idx]))
            label = cls_names[best_pos]
            for obj, pred_name in zip(objects, cls_names):
                name_node = obj.find("name")
                if name_node is None:
                    name_node = ET.SubElement(obj, "name")
                name_node.text = pred_name

    folder_node = xml_root.find("folder")
    if folder_node is None:
        folder_node = ET.SubElement(xml_root, "folder")
    folder_node.text = label
    return label, tree


def move_pair(image_path: Path, xml_path: Path, target_dir: Path, tree: ET.ElementTree, copy_mode: bool) -> tuple[Path, Path]:
    target_dir.mkdir(parents=True, exist_ok=True)
    target_image = safe_target_path(target_dir / image_path.name)
    target_xml = target_image.with_suffix(".xml")

    if copy_mode:
        shutil.copy2(image_path, target_image)
    elif image_path.resolve() != target_image.resolve():
        shutil.move(str(image_path), target_image)

    tree.write(target_xml, encoding="utf-8")

    if not copy_mode and xml_path.exists() and xml_path.resolve() != target_xml.resolve():
        xml_path.unlink()

    return target_image, target_xml


def main() -> None:
    args = parse_args()
    root = args.root
    model = CoilClsModel(config=str(args.classifier_config))

    processed = 0
    errors = 0
    moved = 0
    same_folder = 0

    for xml_path in iter_xml_files(root):
        image_path = find_image_for_xml(xml_path)
        if image_path is None:
            print(f"[skip] image not found: {xml_path}")
            errors += 1
            continue

        try:
            label, tree = predict_label(model, image_path, xml_path, args.batch_size)
            target_dir = root / label
            original_dir = image_path.parent
            move_pair(image_path, xml_path, target_dir, tree, args.copy)
            processed += 1
            if original_dir.resolve() == target_dir.resolve():
                same_folder += 1
            else:
                moved += 1
            print(f"[ok] {image_path.name} -> {label}")
        except Exception as e:
            errors += 1
            print(f"[error] {xml_path}: {e}")

    print(
        f"[done] root={root} processed={processed} moved={moved} same_folder={same_folder} errors={errors}"
    )


if __name__ == "__main__":
    main()
