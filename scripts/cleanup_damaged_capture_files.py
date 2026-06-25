from __future__ import annotations

import argparse
import os
import time
from pathlib import Path

import numpy as np
from PIL import Image


PRODUCTION_ROOTS = [
    Path(r"F:\Cap_L_U"),
    Path(r"F:\Cap_L_M"),
    Path(r"F:\Cap_L_D"),
    Path(r"G:\Cap_S_U"),
    Path(r"G:\Cap_S_M"),
    Path(r"G:\Cap_S_D"),
    Path(r"D:\Save_S"),
    Path(r"E:\Save_L"),
]

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp"}
LEGACY_RAW_SUFFIXES = {".bmp", ".npy"}


def iter_files(root: Path):
    stack = [root]
    while stack:
        folder = stack.pop()
        try:
            with os.scandir(folder) as entries:
                for entry in entries:
                    try:
                        if entry.is_dir(follow_symlinks=False):
                            stack.append(Path(entry.path))
                        elif entry.is_file(follow_symlinks=False):
                            yield Path(entry.path)
                    except OSError:
                        continue
        except OSError:
                    continue


def iter_scan_roots(root: Path, latest_folders: int | None):
    if latest_folders is None or latest_folders <= 0:
        yield root
        return

    folders = []
    try:
        with os.scandir(root) as entries:
            for entry in entries:
                try:
                    if entry.is_dir(follow_symlinks=False) and entry.name.isdigit():
                        folders.append(Path(entry.path))
                except OSError:
                    continue
    except OSError:
        return
    folders.sort(key=lambda path: int(path.name), reverse=True)
    for folder in folders[:latest_folders]:
        yield folder


def is_old_enough(path: Path, min_age_seconds: int) -> bool:
    try:
        return time.time() - path.stat().st_mtime >= min_age_seconds
    except OSError:
        return False


def is_damaged_image(path: Path) -> tuple[bool, str]:
    try:
        if path.stat().st_size <= 0:
            return True, "zero-size"
        with Image.open(path) as image:
            image.verify()
        return False, ""
    except Exception as e:
        return True, type(e).__name__


def is_damaged_numpy(path: Path) -> tuple[bool, str]:
    try:
        if path.stat().st_size <= 0:
            return True, "zero-size"
        if path.suffix.lower() == ".npz":
            with np.load(path) as data:
                if not data.files:
                    return True, "empty-npz"
        else:
            np.load(path, mmap_mode="r")
        return False, ""
    except Exception as e:
        return True, type(e).__name__


def delete_file(path: Path, execute: bool) -> bool:
    if not execute:
        return True
    try:
        path.unlink()
        return True
    except OSError as e:
        print(f"[skip] delete failed: {path} {e}")
        return False


def log_deleted(message: str, printed: list[int], print_limit: int) -> None:
    if printed[0] < print_limit:
        print(message)
    elif printed[0] == print_limit:
        print(f"[more] output truncated after {print_limit} deleted paths")
    printed[0] += 1


def scan_root(root: Path, execute: bool, min_age_seconds: int, delete_legacy_raw: bool,
              check_npz: bool, print_limit: int, latest_folders: int | None) -> dict[str, int]:
    stats = {
        "files": 0,
        "legacy_deleted": 0,
        "damaged_deleted": 0,
        "skipped_recent": 0,
        "errors": 0,
    }
    printed = [0]
    for scan_root_path in iter_scan_roots(root, latest_folders):
        for path in iter_files(scan_root_path):
            stats["files"] += 1
            suffix = path.suffix.lower()
            if suffix not in IMAGE_SUFFIXES and suffix not in {".npy", ".npz"}:
                continue
            if not is_old_enough(path, min_age_seconds):
                stats["skipped_recent"] += 1
                continue

            if delete_legacy_raw and suffix in LEGACY_RAW_SUFFIXES:
                if delete_file(path, execute):
                    stats["legacy_deleted"] += 1
                    log_deleted(f"[legacy] {path}", printed, print_limit)
                continue

            damaged = False
            reason = ""
            if suffix in IMAGE_SUFFIXES:
                damaged, reason = is_damaged_image(path)
            elif check_npz and suffix in {".npy", ".npz"}:
                damaged, reason = is_damaged_numpy(path)

            if damaged:
                if delete_file(path, execute):
                    stats["damaged_deleted"] += 1
                    log_deleted(f"[damaged:{reason}] {path}", printed, print_limit)
    return stats


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Clean damaged images and legacy bmp/npy files from LG_3D data roots.")
    parser.add_argument("--execute", action="store_true", help="Actually delete files. Without this it is a dry run.")
    parser.add_argument("--delete-legacy-raw", action="store_true", help="Delete all old .bmp and .npy files.")
    parser.add_argument("--check-npz", action="store_true", help="Also verify .npz files. This is slower.")
    parser.add_argument("--min-age-minutes", type=int, default=10, help="Skip files modified more recently than this.")
    parser.add_argument("--print-limit", type=int, default=200, help="Maximum deleted paths to print per root.")
    parser.add_argument("--latest-folders", type=int, default=300, help="Only scan latest numeric coil folders per root; 0 means full scan.")
    parser.add_argument("--root", action="append", type=Path, help="Override/add root to scan.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    roots = args.root or PRODUCTION_ROOTS
    min_age_seconds = max(args.min_age_minutes, 0) * 60
    print(
        f"cleanup mode={'execute' if args.execute else 'dry-run'} "
        f"delete_legacy_raw={args.delete_legacy_raw} min_age_minutes={args.min_age_minutes}"
    )
    totals = {}
    for root in roots:
        root = root.resolve()
        if not root.exists():
            print(f"[missing] {root}")
            continue
        if root not in [item.resolve() for item in PRODUCTION_ROOTS] and args.root is None:
            print(f"[skip] unexpected root: {root}")
            continue
        print(f"[scan] {root}")
        latest_folders = None if args.latest_folders == 0 else args.latest_folders
        stats = scan_root(root, args.execute, min_age_seconds, args.delete_legacy_raw, args.check_npz,
                          args.print_limit, latest_folders)
        totals[str(root)] = stats
        print(f"[done] {root} {stats}")
    print("[summary]")
    for root, stats in totals.items():
        print(root, stats)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
