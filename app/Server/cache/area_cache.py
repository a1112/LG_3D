import logging
import threading
from collections import defaultdict
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from cachetools import TTLCache, cached

from Base.CONFIG import serverConfigProperty
from .base import _resolve_image_path
from .memory_cache import MemoryImageCache


class DiskAreaImageCache(MemoryImageCache):
    def __init__(self, cache_size: int = 32, ttl: int = 200, tile_count: int = 3, max_coils: int = 100) -> None:
        self.tile_count = tile_count
        self.max_coils = max_coils
        super().__init__(cache_size=cache_size, ttl=ttl)

    def _tile_cache_dir(self, path: str) -> Path:
        path_obj = _resolve_image_path(path)
        if path_obj.parent.name in {"jpg", "png"}:
            coil_dir = path_obj.parent.parent
        else:
            coil_dir = path_obj.parent
        return coil_dir / "cache" / "area" / "tild"

    def _read_tile_cache(self, cache_dir: Path, count: int) -> Optional[dict]:
        re_dict = defaultdict(dict)
        for row in range(count):
            for col in range(count):
                tile_path = cache_dir / f"{col}_{row}.jpg"
                if not tile_path.exists():
                    return None
                re_dict[col][row] = tile_path.read_bytes()
        return re_dict

    def _write_tile_cache(self, cache_dir: Path, tiles: dict) -> None:
        cache_dir.mkdir(parents=True, exist_ok=True)
        for col in tiles:
            for row in tiles[col]:
                tile_path = cache_dir / f"{col}_{row}.jpg"
                if not tile_path.exists():
                    tile_path.write_bytes(tiles[col][row])

    def _generate_tiles(self, path: str, count: int) -> Optional[dict]:
        image_bytes = self._cache_image_byte(path)
        if image_bytes is None:
            return None
        np_arr = np.frombuffer(image_bytes, dtype=np.uint8)
        image = cv2.imdecode(np_arr, cv2.IMREAD_GRAYSCALE)
        if image is None:
            logging.error("cv2 imdecode failed for %s", path)
            return None
        h, w = image.shape[:2]
        w_width = w // count
        h_height = h // count
        re_dict = defaultdict(dict)
        for row in range(count):
            for col in range(count):
                tile = image[col * h_height:(col + 1) * h_height, row * w_width:(row + 1) * w_width]
                ok, buf = cv2.imencode(".jpg", tile)
                if not ok:
                    logging.error("cv2 imencode failed for %s row=%s col=%s", path, row, col)
                    return None
                re_dict[col][row] = buf.tobytes()
        return re_dict

    def _build_clip_cache(self):
        @cached(cache=TTLCache(maxsize=self.cache_size, ttl=self.ttl))
        def _load_image_clip(path: str, count: int) -> Optional[dict]:
            if count <= 0:
                return None
            count = self.tile_count
            cache_dir = self._tile_cache_dir(path)
            tiles = self._read_tile_cache(cache_dir, count)
            if tiles is not None:
                return tiles
            tiles = self._generate_tiles(path, count)
            if tiles is None:
                return None
            self._write_tile_cache(cache_dir, tiles)
            return tiles

        return _load_image_clip

    def _prefetch_latest_tiles(self) -> None:
        try:
            surfaces = serverConfigProperty.surfaceConfigPropertyDict.values()
        except Exception:
            return
        for surface in surfaces:
            save_dir = Path(surface.saveFolder)
            if not save_dir.exists():
                continue
            coil_ids = []
            for child in save_dir.iterdir():
                if not child.is_dir():
                    continue
                try:
                    coil_ids.append(int(child.name))
                except ValueError:
                    continue
            coil_ids.sort()
            if len(coil_ids) > self.max_coils:
                coil_ids = coil_ids[-self.max_coils:]
            for coil_id in coil_ids:
                try:
                    path = surface.get_file(str(coil_id), "AREA")
                    cache_dir = self._tile_cache_dir(path)
                    if self._read_tile_cache(cache_dir, self.tile_count) is not None:
                        continue
                    tiles = self._generate_tiles(path, self.tile_count)
                    if tiles is not None:
                        self._write_tile_cache(cache_dir, tiles)
                except Exception:
                    logging.debug("prefetch tile cache failed for %s %s", surface.key, coil_id, exc_info=True)

    def startup(self) -> None:
        thread = threading.Thread(target=self._prefetch_latest_tiles, name="area-tile-cache", daemon=True)
        thread.start()
