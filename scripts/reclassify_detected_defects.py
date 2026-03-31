import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import List
from xml.etree import ElementTree as ET

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

MODEL14_NAMES = [
    "刮丝",
    "小型缺陷",
    "折叠",
    "毛刺",
    "烂边",
    "背景",
    "背景_塔形",
    "背景_头尾",
    "背景_小型",
    "背景_打包带",
    "背景_数据脏污",
    "背景_边部",
    "脏污",
    "边部褶皱",
]

MODEL14_TO_8 = {
    "刮丝": "刮丝",
    "小型缺陷": "小型缺陷",
    "折叠": "折叠",
    "毛刺": "毛刺",
    "烂边": "烂边",
    "背景": "背景",
    "背景_塔形": "背景",
    "背景_头尾": "背景",
    "背景_小型": "背景",
    "背景_打包带": "背景",
    "背景_数据脏污": "背景",
    "背景_边部": "背景",
    "脏污": "脏污",
    "边部褶皱": "边部褶皱",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reclassify detected defects from image+xml using classifier and save back into category folders."
    )
    parser.add_argument("--root", default=r"D:\检出优化\折叠检出", help="Root folder containing category subfolders.")
    parser.add_argument(
        "--classifier-config",
        default=r"D:\CONFIG_3D\model\classifier\classifier.json",
        help="Classifier config path.",
    )
    parser.add_argument("--batch-size", type=int, default=32, help="Classifier batch size.")
    parser.add_argument("--limit", type=int, default=0, help="Max xml files to process. 0 means no limit.")
    parser.add_argument("--copy", action="store_true", help="Copy instead of move.")
    return parser.parse_args()


def build_runtime_classifier_config(src_config: Path) -> Path:
    checkpoint_path = (src_config.parent / "efficientnetv2_rw_s.tar").resolve()
    config = {
        "model_name": "efficientnetv2_rw_s",
        "checkpoint_path": str(checkpoint_path),
        "in_chans": 3,
        "names": MODEL14_NAMES,
    }
    tmp_dir = Path(tempfile.gettempdir())
    tmp_path = tmp_dir / "lg3d_classifier_runtime_14.json"
    tmp_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    return tmp_path


def reserve_path(path: Path) -> Path:
    if not path.exists():
        return path
    index = 1
    while True:
        candidate = path.with_name(f"{path.stem}_{index}{path.suffix}")
        if not candidate.exists():
            return candidate
        index += 1


def find_image_for_xml(xml_path: Path) -> Path | None:
    for suffix in (".png", ".jpg", ".jpeg", ".bmp"):
        candidate = xml_path.with_suffix(suffix)
        if candidate.exists():
            return candidate
    return None


def extract_crops(image: Image.Image, xml_root: ET.Element) -> tuple[List[Image.Image], List[ET.Element]]:
    crops = []
    objects = []
    for obj in xml_root.findall("object"):
        bbox = obj.find("bndbox")
        if bbox is None:
            continue
        try:
            xmin = max(0, int(float(bbox.findtext("xmin", "0"))))
            ymin = max(0, int(float(bbox.findtext("ymin", "0"))))
            xmax = min(image.width, int(float(bbox.findtext("xmax", "0"))))
            ymax = min(image.height, int(float(bbox.findtext("ymax", "0"))))
        except ValueError:
            continue
        if xmin >= xmax or ymin >= ymax:
            continue
        crops.append(image.crop((xmin, ymin, xmax, ymax)))
        objects.append(obj)
    return crops, objects


def normalize_label(index: int) -> str:
    if 0 <= index < len(MODEL14_NAMES):
        return MODEL14_TO_8.get(MODEL14_NAMES[index], CLASS_NAMES[0])
    return CLASS_NAMES[0]


def reclassify_one(xml_path: Path, model: CoilClsModel, batch_size: int, copy_mode: bool) -> dict:
    image_path = find_image_for_xml(xml_path)
    if image_path is None:
        raise FileNotFoundError(f"image not found for xml: {xml_path}")

    tree = ET.parse(xml_path)
    xml_root = tree.getroot()

    with Image.open(image_path) as image:
        rgb_image = image.convert("RGB")
        crops, objects = extract_crops(rgb_image, xml_root)

    if not crops:
        target_label = CLASS_NAMES[0]
    else:
        cls_indices, cls_confs, _ = model.predict_image(crops, bach_size=batch_size)
        if not cls_indices:
            target_label = CLASS_NAMES[0]
        else:
            best_idx = 0
            best_conf = -1.0
            for obj, cls_index, cls_conf in zip(objects, cls_indices, cls_confs):
                label = normalize_label(int(cls_index))
                obj.find("name").text = label
                if float(cls_conf) > best_conf:
                    best_conf = float(cls_conf)
                    best_idx = int(cls_index)
            target_label = normalize_label(best_idx)

    folder_node = xml_root.find("folder")
    if folder_node is not None:
        folder_node.text = target_label

    target_dir = xml_path.parents[1] / target_label
    target_dir.mkdir(parents=True, exist_ok=True)

    target_image = reserve_path(target_dir / image_path.name)
    target_xml = target_image.with_suffix(".xml")

    if copy_mode:
        shutil.copy2(image_path, target_image)
    else:
        shutil.move(str(image_path), target_image)

    tree.write(target_xml, encoding="utf-8")

    if not copy_mode and xml_path.exists():
        xml_path.unlink()

    return {
        "xml": str(xml_path),
        "image": str(image_path),
        "target_label": target_label,
        "target_image": str(target_image),
        "target_xml": str(target_xml),
    }


def main() -> None:
    args = parse_args()
    root = Path(args.root)
    runtime_config = build_runtime_classifier_config(Path(args.classifier_config))
    model = CoilClsModel(config=str(runtime_config))

    xml_files = sorted(root.rglob("*.xml"))
    if args.limit:
        xml_files = xml_files[:args.limit]

    processed = 0
    errors = 0
    for xml_path in xml_files:
        try:
            result = reclassify_one(xml_path, model, args.batch_size, args.copy)
            processed += 1
            print(f"[ok] {result['xml']} -> {result['target_label']}")
        except Exception as exc:
            errors += 1
            print(f"[error] {xml_path}: {exc}")

    print(f"[done] processed={processed} errors={errors} root={root}")


if __name__ == "__main__":
    main()
