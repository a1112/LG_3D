from __future__ import annotations

import argparse
import shutil
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable


DEFAULT_SOURCES = (
    Path(r"E:\Save_L"),
    Path(r"D:\Save_S"),
)
DEFAULT_TARGET = Path("D:/\u68c0\u51fa\u4f18\u5316")
FOLD_CLASS_NAME = "\u6298\u53e0"


@dataclass
class CopyStats:
    copied: int = 0
    skipped_existing: int = 0
    missing_detection: int = 0
    missing_class_dir: int = 0
    errors: int = 0
    scanned_coils: int = 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Copy recent detection data and all folded detection data into D:\\u68c0\\u51fa\\u4f18\\u5316."
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Copy all detection categories from coils updated within the last N days. Default: 30.",
    )
    parser.add_argument(
        "--target",
        type=Path,
        default=DEFAULT_TARGET,
        help="Destination root directory. Default: D:\\u68c0\\u51fa\\u4f18\\u5316",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned actions without copying files.",
    )
    return parser.parse_args()


def iter_recent_coils(source_root: Path, cutoff: datetime) -> Iterable[Path]:
    for coil_dir in source_root.iterdir():
        if not coil_dir.is_dir():
            continue
        if datetime.fromtimestamp(coil_dir.stat().st_mtime) >= cutoff:
            yield coil_dir


def copy_file(src: Path, dst: Path, stats: CopyStats, dry_run: bool, log_lines: list[str]) -> None:
    if dst.exists():
        if dst.stat().st_size == src.stat().st_size:
            stats.skipped_existing += 1
            return

        stem = dst.stem
        suffix = dst.suffix
        index = 1
        while True:
            alt_dst = dst.with_name(f"{stem}_dup{index}{suffix}")
            if not alt_dst.exists():
                dst = alt_dst
                break
            index += 1

    dst.parent.mkdir(parents=True, exist_ok=True)
    if dry_run:
        stats.copied += 1
        return

    shutil.copy2(src, dst)
    stats.copied += 1


def copy_detection_tree(
    detection_dir: Path,
    target_root: Path,
    stats: CopyStats,
    dry_run: bool,
    log_lines: list[str],
    only_class: str | None = None,
) -> None:
    if not detection_dir.exists():
        stats.missing_detection += 1
        return

    class_dirs = [path for path in detection_dir.iterdir() if path.is_dir()]
    if only_class is not None:
        class_dirs = [path for path in class_dirs if path.name == only_class]

    if only_class is not None and not class_dirs:
        stats.missing_class_dir += 1
        return

    for class_dir in class_dirs:
        destination_dir = target_root / class_dir.name
        for src_file in class_dir.iterdir():
            if not src_file.is_file():
                continue
            dst_file = destination_dir / src_file.name
            try:
                copy_file(src_file, dst_file, stats, dry_run, log_lines)
            except Exception as exc:
                stats.errors += 1
                log_lines.append(f"[ERROR] copy failed: {src_file} -> {dst_file}: {exc}")


def write_log(target_root: Path, log_lines: list[str]) -> Path:
    log_file = target_root / f"copy_detection_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    log_file.write_text("\n".join(log_lines), encoding="utf-8")
    return log_file


def main() -> int:
    args = parse_args()
    target_root = args.target
    target_root.mkdir(parents=True, exist_ok=True)

    cutoff = datetime.now() - timedelta(days=args.days)
    stats = CopyStats()
    log_lines: list[str] = [
        f"start: {datetime.now().isoformat(sep=' ', timespec='seconds')}",
        f"target: {target_root}",
        f"recent_cutoff: {cutoff.isoformat(sep=' ', timespec='seconds')}",
        f"dry_run: {args.dry_run}",
        "",
        "[Phase 1] Recent detection copy",
    ]

    for source_root in DEFAULT_SOURCES:
        if not source_root.exists():
            stats.errors += 1
            log_lines.append(f"[ERROR] source root does not exist: {source_root}")
            continue

        log_lines.append(f"scan recent coils: {source_root}")
        for coil_dir in iter_recent_coils(source_root, cutoff):
            stats.scanned_coils += 1
            copy_detection_tree(
                detection_dir=coil_dir / "detection",
                target_root=target_root,
                stats=stats,
                dry_run=args.dry_run,
                log_lines=log_lines,
            )

    log_lines.extend(("", f"[Phase 2] All {FOLD_CLASS_NAME} detection copy"))
    for source_root in DEFAULT_SOURCES:
        if not source_root.exists():
            continue

        log_lines.append(f"scan all coils for {FOLD_CLASS_NAME}: {source_root}")
        for coil_dir in source_root.iterdir():
            if not coil_dir.is_dir():
                continue
            copy_detection_tree(
                detection_dir=coil_dir / "detection",
                target_root=target_root,
                stats=stats,
                dry_run=args.dry_run,
                log_lines=log_lines,
                only_class=FOLD_CLASS_NAME,
            )

    log_lines.extend(
        (
            "",
            "[Summary]",
            f"scanned_coils_recent: {stats.scanned_coils}",
            f"copied: {stats.copied}",
            f"skipped_existing: {stats.skipped_existing}",
            f"missing_detection: {stats.missing_detection}",
            f"missing_{FOLD_CLASS_NAME}: {stats.missing_class_dir}",
            f"errors: {stats.errors}",
            f"end: {datetime.now().isoformat(sep=' ', timespec='seconds')}",
        )
    )

    log_file = write_log(target_root, log_lines)
    print(f"log_file={log_file}")
    print(f"scanned_coils_recent={stats.scanned_coils}")
    print(f"copied={stats.copied}")
    print(f"skipped_existing={stats.skipped_existing}")
    print(f"missing_detection={stats.missing_detection}")
    print(f"missing_{FOLD_CLASS_NAME}={stats.missing_class_dir}")
    print(f"errors={stats.errors}")
    return 0 if stats.errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
