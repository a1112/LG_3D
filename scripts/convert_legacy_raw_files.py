from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Iterable

import numpy as np
from PIL import Image


DEFAULT_SERVER_CONFIG = Path(r"D:\CONFIG_3D\configs\Server3D.json")
DEFAULT_CAPTURE_CONFIG = Path(r"D:\CONFIG_3D\capture_config\CapTure.json")
SKIP_DIR_NAMES = {"cache", "preview", "detection", "classifier", "json", "link"}
LEGACY_GLOBS = ("*.bmp", "*.BMP", "*.npy", "*.NPY")


def _read_json(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}


def configured_roots() -> list[Path]:
    roots: list[Path] = []

    server_config = _read_json(DEFAULT_SERVER_CONFIG)
    for surface in server_config.get("surface", []):
        save_folder = surface.get("saveFolder")
        if save_folder:
            roots.append(Path(save_folder))
        for folder in surface.get("folderList", []):
            source = folder.get("source")
            if source:
                roots.append(Path(source))

    capture_config = _read_json(DEFAULT_CAPTURE_CONFIG)
    for camera in capture_config.get("camera_config_list", []):
        config = camera.get("config", {})
        save_folder = config.get("saveFolder")
        key = config.get("key")
        if save_folder and key:
            roots.append(Path(save_folder) / key)

    return dedupe_existing_roots(roots)


def dedupe_existing_roots(roots: Iterable[Path]) -> list[Path]:
    resolved: dict[str, Path] = {}
    for root in roots:
        try:
            path = root.resolve()
        except OSError:
            path = root.absolute()
        if path.exists():
            resolved[str(path).lower()] = path
    return sorted(
        resolved.values(),
        key=lambda item: (0 if "cap_" in str(item).lower() else 1, str(item).lower()),
    )


def iter_legacy_files(roots: Iterable[Path], min_age_seconds: float) -> Iterable[Path]:
    now = time.time()
    for root in roots:
        if os.name == "nt":
            yield from iter_cmd_legacy_files(root, now, min_age_seconds)
            continue
        if shutil.which("rg"):
            yield from iter_rg_legacy_files(root, now, min_age_seconds)
            continue
        if root.name.lower().startswith("cap_"):
            yield from iter_capture_legacy_files(root, now, min_age_seconds)
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [name for name in dirnames if name.lower() not in SKIP_DIR_NAMES]
            for filename in filenames:
                yield from legacy_candidate(Path(dirpath) / filename, now, min_age_seconds)


def iter_cmd_legacy_files(root: Path, now: float, min_age_seconds: float) -> Iterable[Path]:
    if root.name.lower().startswith("cap_"):
        patterns = [
            str(root / "*" / "2d" / "*.bmp"),
            str(root / "*" / "3d" / "*.npy"),
        ]
    else:
        patterns = [
            str(root / "*.bmp"),
            str(root / "*.npy"),
        ]
    quoted_patterns = " ".join(f'"{pattern}"' for pattern in patterns)
    command = f"dir /b /s {quoted_patterns} 2>NUL"
    try:
        process = subprocess.Popen(
            ["cmd", "/d", "/c", command],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError:
        if root.name.lower().startswith("cap_"):
            yield from iter_capture_legacy_files(root, now, min_age_seconds)
        else:
            for dirpath, dirnames, filenames in os.walk(root):
                dirnames[:] = [name for name in dirnames if name.lower() not in SKIP_DIR_NAMES]
                for filename in filenames:
                    yield from legacy_candidate(Path(dirpath) / filename, now, min_age_seconds)
        return

    assert process.stdout is not None
    for line in process.stdout:
        text = line.strip()
        if text:
            yield from legacy_candidate(Path(text), now, min_age_seconds)
    process.wait()


def iter_rg_legacy_files(root: Path, now: float, min_age_seconds: float) -> Iterable[Path]:
    command = ["rg", "--files", str(root)]
    for pattern in LEGACY_GLOBS:
        command.extend(["-g", pattern])
    for directory in SKIP_DIR_NAMES:
        command.extend(["-g", f"!**/{directory}/**"])
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError:
        if root.name.lower().startswith("cap_"):
            yield from iter_capture_legacy_files(root, now, min_age_seconds)
        else:
            for dirpath, dirnames, filenames in os.walk(root):
                dirnames[:] = [name for name in dirnames if name.lower() not in SKIP_DIR_NAMES]
                for filename in filenames:
                    yield from legacy_candidate(Path(dirpath) / filename, now, min_age_seconds)
        return

    assert process.stdout is not None
    for line in process.stdout:
        text = line.strip()
        if text:
            yield from legacy_candidate(Path(text), now, min_age_seconds)
    process.wait()


def iter_capture_legacy_files(root: Path, now: float, min_age_seconds: float) -> Iterable[Path]:
    try:
        coil_entries = list(os.scandir(root))
    except OSError:
        return
    for coil_entry in coil_entries:
        if not coil_entry.is_dir():
            continue
        for subdir_name in ("2d", "3d"):
            subdir = Path(coil_entry.path) / subdir_name
            try:
                entries = list(os.scandir(subdir))
            except OSError:
                continue
            for entry in entries:
                if entry.is_file():
                    yield from legacy_candidate(Path(entry.path), now, min_age_seconds)


def legacy_candidate(path: Path, now: float, min_age_seconds: float) -> Iterable[Path]:
    suffix = path.suffix.lower()
    if suffix not in {".bmp", ".npy"}:
        return
    try:
        age = now - path.stat().st_mtime
    except OSError:
        return
    if age < min_age_seconds:
        yield path.with_name(path.name + ".recent-skip")
        return
    yield path


def convert_bmp(path: Path, quality: int) -> tuple[str, str]:
    target = path.with_suffix(".jpg")
    if target.exists() and target.stat().st_size > 0:
        try:
            path.unlink()
            return "converted", str(path)
        except PermissionError:
            return "locked_original", str(path)
    temp = target.with_name(target.name + ".tmp")
    with Image.open(path) as image:
        if image.mode in {"RGBA", "P", "LA"}:
            image = image.convert("RGB")
        target.parent.mkdir(parents=True, exist_ok=True)
        image.save(temp, format="JPEG", quality=quality, optimize=True)
    os.replace(temp, target)
    try:
        path.unlink()
    except PermissionError:
        return "locked_original", str(path)
    return "converted", str(path)


def convert_npy(path: Path) -> tuple[str, str]:
    target = path.with_suffix(".npz")
    if target.exists() and target.stat().st_size > 0:
        try:
            path.unlink()
            return "converted", str(path)
        except PermissionError:
            return "locked_original", str(path)
    temp = target.with_name(target.name + ".tmp")
    array = np.load(path, allow_pickle=False)
    target.parent.mkdir(parents=True, exist_ok=True)
    with temp.open("wb") as file:
        np.savez_compressed(file, array=array)
    os.replace(temp, target)
    try:
        path.unlink()
    except PermissionError:
        return "locked_original", str(path)
    return "converted", str(path)


def convert_one(path: Path, quality: int) -> tuple[str, str]:
    if path.name.endswith(".recent-skip"):
        return "recent_skip", str(path.with_name(path.name.removesuffix(".recent-skip")))
    try:
        suffix = path.suffix.lower()
        if suffix == ".bmp":
            return convert_bmp(path, quality)
        if suffix == ".npy":
            return convert_npy(path)
        return "ignored", str(path)
    except Exception as exc:
        if isinstance(exc, PermissionError) or getattr(exc, "winerror", None) == 32:
            return "locked_original", str(path)
        for temp in (path.with_suffix(".jpg").with_name(path.with_suffix(".jpg").name + ".tmp"),
                     path.with_suffix(".npz").with_name(path.with_suffix(".npz").name + ".tmp")):
            try:
                temp.unlink(missing_ok=True)
            except OSError:
                pass
        return "failed", f"{path} :: {type(exc).__name__}: {exc}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert legacy BMP/NPY production data to JPG/NPZ.")
    parser.add_argument("--root", action="append", type=Path, help="Additional root to scan.")
    parser.add_argument("--min-age-seconds", type=float, default=180.0)
    parser.add_argument("--workers", type=int, default=max(2, min(4, (os.cpu_count() or 4) // 2)))
    parser.add_argument("--quality", type=int, default=95)
    parser.add_argument("--log-file", type=Path)
    return parser.parse_args()


def log_line(log_file: Path | None, text: str) -> None:
    print(text, flush=True)
    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        with log_file.open("a", encoding="utf-8") as file:
            file.write(text + "\n")


def main() -> int:
    args = parse_args()
    roots = configured_roots()
    if args.root:
        roots = dedupe_existing_roots([*roots, *args.root])

    log_line(args.log_file, "roots:")
    for root in roots:
        log_line(args.log_file, f"  {root}")

    counts = {"converted": 0, "failed": 0, "recent_skip": 0, "ignored": 0, "locked_original": 0}
    start = time.time()
    queued = 0
    completed = 0
    max_pending = max(args.workers * 8, 8)

    def handle_result(future: concurrent.futures.Future) -> None:
        nonlocal completed
        status, detail = future.result()
        completed += 1
        counts[status] = counts.get(status, 0) + 1
        if status == "failed":
            log_line(args.log_file, f"FAILED {detail}")
        if completed % 100 == 0:
            elapsed = time.time() - start
            log_line(
                args.log_file,
                f"progress={completed}/{queued} converted={counts.get('converted', 0)} "
                f"locked={counts.get('locked_original', 0)} recent_skip={counts.get('recent_skip', 0)} "
                f"failed={counts.get('failed', 0)} "
                f"elapsed_s={elapsed:.1f}",
            )

    log_line(args.log_file, f"streaming_scan workers={args.workers} min_age_seconds={args.min_age_seconds}")
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        pending: set[concurrent.futures.Future] = set()
        for root in roots:
            log_line(args.log_file, f"scanning_root={root}")
            for path in iter_legacy_files([root], args.min_age_seconds):
                queued += 1
                pending.add(executor.submit(convert_one, path, args.quality))
                if len(pending) >= max_pending:
                    done, pending = concurrent.futures.wait(
                        pending,
                        return_when=concurrent.futures.FIRST_COMPLETED,
                    )
                    for future in done:
                        handle_result(future)
            log_line(args.log_file, f"finished_root={root} queued={queued} completed={completed}")

        while pending:
            done, pending = concurrent.futures.wait(
                pending,
                return_when=concurrent.futures.FIRST_COMPLETED,
            )
            for future in done:
                handle_result(future)

    log_line(args.log_file, f"done queued={queued} completed={completed} {counts}")
    return 1 if counts.get("failed", 0) else 0


if __name__ == "__main__":
    sys.exit(main())
