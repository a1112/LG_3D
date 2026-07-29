from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


DEFAULT_SOURCES = ((Path(r"D:\Save_S"), "S"), (Path(r"E:\Save_L"), "L"))
IMAGE_SUFFIXES = {".bmp", ".jpeg", ".jpg", ".png", ".tif", ".tiff", ".webp"}


@dataclass
class Stats:
    scanned_coils: int = 0
    selected_coils: int = 0
    detection_coils: int = 0
    classifier_coils: int = 0
    copied_files: int = 0
    copied_bytes: int = 0
    skipped_identical: int = 0
    errors: int = 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect recent defect images, XML annotations, and classifier crops."
    )
    parser.add_argument("--since", type=datetime.fromisoformat, required=True)
    parser.add_argument("--target", type=Path, required=True)
    return parser.parse_args()


def copy_file(source: Path, destination: Path, stats: Stats) -> str:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if destination.stat().st_size == source.stat().st_size:
            stats.skipped_identical += 1
            return "skipped_identical"
        raise FileExistsError(f"destination collision: {destination}")
    shutil.copy2(source, destination)
    source_size = source.stat().st_size
    stats.copied_files += 1
    stats.copied_bytes += source_size
    return "copied"


def iter_class_files(root: Path):
    if not root.is_dir():
        return
    with os.scandir(root) as class_entries:
        for class_entry in class_entries:
            if not class_entry.is_dir(follow_symlinks=False):
                continue
            class_dir = Path(class_entry.path)
            with os.scandir(class_dir) as file_entries:
                for file_entry in file_entries:
                    if file_entry.is_file(follow_symlinks=False):
                        yield class_dir.name, Path(file_entry.path)


def main() -> int:
    args = parse_args()
    target = args.target.resolve()
    target.mkdir(parents=True, exist_ok=True)
    manifest_path = target / "manifest.csv"
    stats = Stats()
    counts: Counter[str] = Counter()
    errors: list[str] = []

    with manifest_path.open("w", encoding="utf-8-sig", newline="") as manifest_file:
        writer = csv.writer(manifest_file)
        writer.writerow(
            [
                "kind",
                "surface",
                "coil",
                "class_name",
                "source_path",
                "destination_path",
                "size_bytes",
                "modified_time",
                "status",
            ]
        )

        for source_root, surface in DEFAULT_SOURCES:
            if not source_root.is_dir():
                message = f"missing source root: {source_root}"
                errors.append(message)
                stats.errors += 1
                continue

            with os.scandir(source_root) as coil_entries:
                for coil_entry in coil_entries:
                    if not coil_entry.is_dir(follow_symlinks=False):
                        continue
                    stats.scanned_coils += 1
                    coil_modified = datetime.fromtimestamp(coil_entry.stat().st_mtime)
                    if coil_modified < args.since:
                        continue
                    stats.selected_coils += 1
                    coil_dir = Path(coil_entry.path)

                    for kind in ("detection", "classifier"):
                        kind_root = coil_dir / kind
                        if not kind_root.is_dir():
                            continue
                        if kind == "detection":
                            stats.detection_coils += 1
                        else:
                            stats.classifier_coils += 1

                        for class_name, source_file in iter_class_files(kind_root):
                            suffix = source_file.suffix.lower()
                            if kind == "classifier" and suffix not in IMAGE_SUFFIXES:
                                continue
                            destination = (
                                target
                                / kind
                                / class_name
                                / f"{surface}_{source_file.name}"
                            )
                            try:
                                status = copy_file(source_file, destination, stats)
                                counts[f"{kind}:{class_name}:{suffix or '[no_ext]'}"] += 1
                                writer.writerow(
                                    [
                                        kind,
                                        surface,
                                        coil_dir.name,
                                        class_name,
                                        str(source_file),
                                        str(destination),
                                        source_file.stat().st_size,
                                        datetime.fromtimestamp(
                                            source_file.stat().st_mtime
                                        ).isoformat(sep=" ", timespec="seconds"),
                                        status,
                                    ]
                                )
                            except Exception as exc:
                                stats.errors += 1
                                errors.append(f"{source_file} -> {destination}: {exc}")

                    if stats.selected_coils % 5000 == 0:
                        print(
                            f"selected_coils={stats.selected_coils} "
                            f"copied_files={stats.copied_files} errors={stats.errors}",
                            flush=True,
                        )

    image_stems: set[tuple[str, str]] = set()
    xml_stems: set[tuple[str, str]] = set()
    detection_root = target / "detection"
    if detection_root.is_dir():
        for class_dir in detection_root.iterdir():
            if not class_dir.is_dir():
                continue
            for file_path in class_dir.iterdir():
                key = (class_dir.name, file_path.stem)
                if file_path.suffix.lower() in IMAGE_SUFFIXES:
                    image_stems.add(key)
                elif file_path.suffix.lower() == ".xml":
                    xml_stems.add(key)

    orphan_images = sorted(image_stems - xml_stems)
    orphan_xml = sorted(xml_stems - image_stems)
    summary = {
        "created_at": datetime.now().isoformat(sep=" ", timespec="seconds"),
        "since": args.since.isoformat(sep=" ", timespec="seconds"),
        "target": str(target),
        "sources": [str(path) for path, _ in DEFAULT_SOURCES],
        "stats": vars(stats),
        "counts": dict(sorted(counts.items())),
        "validation": {
            "detection_image_count": len(image_stems),
            "detection_xml_count": len(xml_stems),
            "paired_detection_samples": len(image_stems & xml_stems),
            "orphan_image_count": len(orphan_images),
            "orphan_xml_count": len(orphan_xml),
        },
    }
    (target / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (target / "errors.txt").write_text("\n".join(errors), encoding="utf-8")
    (target / "orphan_images.txt").write_text(
        "\n".join(f"{class_name}/{stem}" for class_name, stem in orphan_images),
        encoding="utf-8",
    )
    (target / "orphan_xml.txt").write_text(
        "\n".join(f"{class_name}/{stem}" for class_name, stem in orphan_xml),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    return 0 if stats.errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
