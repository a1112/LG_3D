import time
from pathlib import Path
from typing import Iterable


TWO_D_DIR_NAMES = ("2D", "2d")
THREE_D_DIR_NAMES = ("3D", "3d")
TWO_D_PATTERNS = ("*.bmp", "*.jpg")


def _numeric_stem_key(path: Path) -> tuple[int, str]:
    stem = path.name
    for suffix in reversed(path.suffixes):
        if stem.endswith(suffix):
            stem = stem[:-len(suffix)]
    try:
        return int(stem), path.name
    except ValueError:
        return 10**12, path.name


def resolve_capture_dir(source: Path | str, coil_id: str | int, dir_names: Iterable[str]) -> Path:
    coil_dir = Path(source) / str(coil_id)
    dir_names = tuple(dir_names)
    if coil_dir.exists():
        children = {path.name: path for path in coil_dir.iterdir() if path.is_dir()}
        for name in dir_names:
            if name in children:
                return children[name]
        lowered = {path.name.lower(): path for path in children.values()}
        for name in dir_names:
            match = lowered.get(name.lower())
            if match is not None:
                return match
    for name in dir_names:
        candidate = coil_dir / name
        if candidate.exists():
            return candidate
    return coil_dir / dir_names[0]


def sorted_indexed_files(folder: Path | str, patterns: Iterable[str]) -> list[Path]:
    folder = Path(folder)
    files: dict[Path, Path] = {}
    for pattern in patterns:
        for path in folder.glob(pattern):
            if path.is_file():
                files[path.resolve()] = path
    return sorted(files.values(), key=_numeric_stem_key)


def capture_complete(source: Path | str, coil_id: str | int, quiet_seconds: float = 3.2, min_files: int = 4) -> bool:
    source2_d = resolve_capture_dir(source, coil_id, TWO_D_DIR_NAMES)
    if not source2_d.exists():
        return False

    image_files = sorted_indexed_files(source2_d, TWO_D_PATTERNS)
    if len(image_files) < min_files:
        return False

    now = time.time()
    return all(now - image_file.stat().st_mtime >= quiet_seconds for image_file in image_files)
