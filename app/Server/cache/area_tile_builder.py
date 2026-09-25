import logging
import shutil
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from PIL import Image


Image.MAX_IMAGE_PIXELS = None

AREA_TILE_LEVELS: Dict[int, tuple[int, int]] = {
    0: (340, 60),
    1: (682, 70),
    2: (1364, 80),
    3: (2728, 90),
    4: (5460, 95),
}
DEFAULT_AREA_TILE_COUNT = 3


@dataclass
class AreaTileCacheRebuildResult:
    image_path: str
    cache_dir: str
    rebuilt: bool
    width: int = 0
    height: int = 0
    tile_count: int = DEFAULT_AREA_TILE_COUNT
    levels: Optional[List[int]] = None
    tiles: int = 0
    removed_files: int = 0
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "ok": self.rebuilt,
            "image_path": self.image_path,
            "cache_dir": self.cache_dir,
            "width": self.width,
            "height": self.height,
            "tile_count": self.tile_count,
            "levels": self.levels or [],
            "tiles": self.tiles,
            "removed_files": self.removed_files,
            "error": self.error,
        }


def area_tile_cache_base_dir(image_path: Path) -> Path:
    if image_path.parent.name in {"jpg", "png"}:
        coil_dir = image_path.parent.parent
    else:
        coil_dir = image_path.parent
    if image_path.stem.upper() != "AREA":
        return coil_dir / "cache" / "area" / image_path.stem.upper() / "tild"
    return coil_dir / "cache" / "area" / "tild"


def _safe_tile_cache_dir(cache_dir: Path) -> Path:
    resolved = cache_dir.resolve(strict=False)
    parts = [part.lower() for part in resolved.parts]
    if resolved.name.lower() != "tild" or "cache" not in parts or "area" not in parts:
        raise ValueError(f"refuse to remove unexpected AREA tile cache dir: {resolved}")
    return resolved


def _count_files(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for item in path.rglob("*") if item.is_file())


def _resize_tile_bytes(tile_image: Image.Image, target_size: int, quality: int) -> bytes:
    width, height = tile_image.size
    max_dim = max(width, height)
    if max_dim <= target_size:
        buf = BytesIO()
        tile_image.save(buf, format="JPEG", quality=quality)
        return buf.getvalue()

    scale = target_size / max_dim
    new_width = max(1, int(width * scale))
    new_height = max(1, int(height * scale))
    resized = tile_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
    try:
        buf = BytesIO()
        resized.save(buf, format="JPEG", quality=quality)
        return buf.getvalue()
    finally:
        resized.close()


def _normal_levels(levels: Optional[Iterable[int]]) -> List[int]:
    if levels is None:
        return sorted(AREA_TILE_LEVELS)
    result = sorted(set(int(level) for level in levels))
    invalid = [level for level in result if level not in AREA_TILE_LEVELS]
    if invalid:
        raise ValueError(f"invalid AREA tile levels: {invalid}")
    return result


def rebuild_area_tile_cache(image_path: str | Path,
                            *,
                            tile_count: int = DEFAULT_AREA_TILE_COUNT,
                            levels: Optional[Iterable[int]] = None,
                            remove_existing: bool = True) -> AreaTileCacheRebuildResult:
    path = Path(image_path)
    cache_dir = area_tile_cache_base_dir(path)
    level_list = _normal_levels(levels)
    result = AreaTileCacheRebuildResult(image_path=str(path),
                                        cache_dir=str(cache_dir),
                                        rebuilt=False,
                                        tile_count=tile_count,
                                        levels=level_list)

    if tile_count <= 0:
        result.error = f"invalid tile_count={tile_count}"
        return result
    if not path.exists():
        result.error = f"image not found: {path}"
        return result

    try:
        safe_cache_dir = _safe_tile_cache_dir(cache_dir)
        with Image.open(path) as source:
            image = source.convert("L")

        try:
            width, height = image.size
            result.width = width
            result.height = height
            tile_width = width // tile_count
            tile_height = height // tile_count
            if tile_width <= 0 or tile_height <= 0:
                result.error = f"image too small for tile_count={tile_count}: {width}x{height}"
                return result

            if remove_existing and safe_cache_dir.exists():
                result.removed_files = _count_files(safe_cache_dir)
                shutil.rmtree(safe_cache_dir)

            cache_dirs = {}
            for level in level_list:
                level_dir = safe_cache_dir / f"L{level}"
                level_dir.mkdir(parents=True, exist_ok=True)
                cache_dirs[level] = level_dir

            for row in range(tile_count):
                for col in range(tile_count):
                    left = col * tile_width
                    top = row * tile_height
                    right = width if col == tile_count - 1 else left + tile_width
                    bottom = height if row == tile_count - 1 else top + tile_height
                    tile = image.crop((left, top, right, bottom))
                    try:
                        for level in level_list:
                            target_size, quality = AREA_TILE_LEVELS[level]
                            tile_path = cache_dirs[level] / f"{col}_{row}.jpg"
                            if level == 4:
                                tile.save(tile_path, format="JPEG", quality=quality)
                            else:
                                tile_path.write_bytes(_resize_tile_bytes(tile, target_size, quality))
                            result.tiles += 1
                    finally:
                        tile.close()
        finally:
            image.close()
    except Exception as exc:
        logging.exception("failed to rebuild AREA tile cache for %s", path)
        result.error = str(exc)
        return result

    result.rebuilt = True
    return result
