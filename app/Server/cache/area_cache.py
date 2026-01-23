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


# 多级瓦片配置：级别 -> (目标尺寸, JPEG质量)
TILE_LEVELS = {
    0: (340, 60),    # Level 0: 1/16 缩略图 (~20KB)
    1: (682, 70),    # Level 1: 1/8 (~50KB)
    2: (1364, 80),   # Level 2: 1/4 (~120KB)
    3: (2728, 90),   # Level 3: 1/2 (~250KB)
    4: (5460, 95),   # Level 4: 原图瓦片 (~500KB)
}


class DiskAreaImageCache(MemoryImageCache):
    def __init__(self, cache_size: int = 32, ttl: int = 200, tile_count: int = 3, max_coils: int = 100) -> None:
        self.tile_count = tile_count
        self.max_coils = max_coils
        super().__init__(cache_size=cache_size, ttl=ttl)

    def _tile_cache_base_dir(self, path: str) -> Path:
        """获取瓦片缓存基础目录"""
        path_obj = _resolve_image_path(path)
        if path_obj.parent.name in {"jpg", "png"}:
            coil_dir = path_obj.parent.parent
        else:
            coil_dir = path_obj.parent
        return coil_dir / "cache" / "area" / "tild"

    def _tile_cache_dir(self, path: str, level: int = 4) -> Path:
        """获取指定级别的瓦片缓存目录"""
        # 按级别分目录: cache/area/tild/L0/, L1/, L2/, etc.
        return self._tile_cache_base_dir(path) / f"L{level}"

    def _tile_path(self, cache_dir: Path, col: int, row: int) -> Path:
        """获取瓦片文件路径"""
        return cache_dir / f"{col}_{row}.jpg"

    def _read_tile_cache(self, cache_dir: Path, count: int) -> Optional[dict]:
        """读取指定目录下的所有瓦片"""
        re_dict = defaultdict(dict)
        for row in range(count):
            for col in range(count):
                tile_path = self._tile_path(cache_dir, col, row)
                if not tile_path.exists():
                    return None
                re_dict[col][row] = tile_path.read_bytes()
        return re_dict

    def _write_tile_cache(self, cache_dir: Path, tiles: dict) -> None:
        """写入瓦片到指定目录"""
        cache_dir.mkdir(parents=True, exist_ok=True)
        for col in tiles:
            for row in tiles[col]:
                tile_path = self._tile_path(cache_dir, col, row)
                if not tile_path.exists():
                    tile_path.write_bytes(tiles[col][row])

    def _resize_tile_bytes(self, tile_bytes: bytes, target_size: int, quality: int) -> bytes:
        """调整瓦片尺寸"""
        np_arr = np.frombuffer(tile_bytes, dtype=np.uint8)
        tile = cv2.imdecode(np_arr, cv2.IMREAD_GRAYSCALE)
        if tile is None:
            return tile_bytes

        h, w = tile.shape[:2]
        max_dim = max(h, w)

        if max_dim <= target_size:
            # 不需要缩小，只调整质量
            ok, buf = cv2.imencode(".jpg", tile, [cv2.IMWRITE_JPEG_QUALITY, quality])
            return buf.tobytes() if ok else tile_bytes

        # 缩小图像
        scale = target_size / max_dim
        new_w = int(w * scale)
        new_h = int(h * scale)
        resized = cv2.resize(tile, (new_w, new_h), interpolation=cv2.INTER_AREA)

        ok, buf = cv2.imencode(".jpg", resized, [cv2.IMWRITE_JPEG_QUALITY, quality])
        return buf.tobytes() if ok else tile_bytes

    def _generate_tiles(self, path: str, count: int) -> Optional[dict]:
        """生成 L4 原图瓦片，并同时生成 L0-L3 的瓦片"""
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

        # 生成 L4 原图瓦片
        l4_tiles = defaultdict(dict)
        for row in range(count):
            for col in range(count):
                tile = image[col * h_height:(col + 1) * h_height, row * w_width:(row + 1) * w_width]
                ok, buf = cv2.imencode(".jpg", tile, [cv2.IMWRITE_JPEG_QUALITY, TILE_LEVELS[4][1]])
                if not ok:
                    logging.error("cv2 imencode failed for %s row=%s col=%s", path, row, col)
                    return None
                l4_tiles[col][row] = buf.tobytes()

        # 保存 L4 瓦片
        l4_cache_dir = self._tile_cache_dir(path, 4)
        self._write_tile_cache(l4_cache_dir, l4_tiles)
        logging.info(f"Saved L4 tiles to {l4_cache_dir}")

        # 同时生成并保存 L0-L3 瓦片（空间换时间）
        for level in range(4):
            target_size, quality = TILE_LEVELS[level]
            level_tiles = defaultdict(dict)
            for col in l4_tiles:
                for row in l4_tiles[col]:
                    resized_bytes = self._resize_tile_bytes(l4_tiles[col][row], target_size, quality)
                    level_tiles[col][row] = resized_bytes

            level_cache_dir = self._tile_cache_dir(path, level)
            self._write_tile_cache(level_cache_dir, level_tiles)
            logging.info(f"Saved L{level} tiles to {level_cache_dir}")

        return l4_tiles

    def get_tile(self, path: str, row: int, col: int, count: int, level: int = 4) -> Optional[bytes]:
        """
        获取指定位置和级别的瓦片

        优先从缓存读取，如果没有则回退到生成模式
        """
        if count <= 0:
            return None

        count = self.tile_count
        cache_dir = self._tile_cache_dir(path, level)

        # 尝试从缓存读取
        tile_path = self._tile_path(cache_dir, col, row)
        if tile_path.exists():
            return tile_path.read_bytes()

        # 缓存不存在，尝试生成所有级别的瓦片
        logging.info(f"Cache miss for L{level} tile ({col},{row}), generating all levels...")
        tiles = self._generate_tiles(path, count)
        if tiles is None:
            return None

        # 重新读取
        tile_path = self._tile_path(cache_dir, col, row)
        if tile_path.exists():
            return tile_path.read_bytes()

        return None

    def get_all_tiles(self, path: str, count: int) -> Optional[dict]:
        """获取所有瓦片（用于兼容旧的 clip_num 接口）"""
        if count <= 0:
            return None
        count = self.tile_count

        # 优先读取 L4
        cache_dir = self._tile_cache_dir(path, 4)
        tiles = self._read_tile_cache(cache_dir, count)

        if tiles is None:
            # 缓存不存在，生成所有级别
            tiles = self._generate_tiles(path, count)

        return tiles

    def _build_clip_cache(self):
        @cached(cache=TTLCache(maxsize=self.cache_size, ttl=self.ttl))
        def _load_image_clip(path: str, count: int) -> Optional[dict]:
            if count <= 0:
                return None
            count = self.tile_count
            return self.get_all_tiles(path, count)
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
                    cache_dir = self._tile_cache_dir(path, 4)
                    if self._read_tile_cache(cache_dir, self.tile_count) is not None:
                        continue
                    # 预生成所有级别
                    logging.info(f"Prefetching all levels for {surface.key} coil {coil_id}")
                    self._generate_tiles(str(path), self.tile_count)
                except Exception:
                    logging.debug("prefetch tile cache failed for %s %s", surface.key, coil_id, exc_info=True)

    def cleanup_old_cache(self) -> None:
        """清理旧版本的瓦片缓存（根目录下的 0_0.jpg 等文件）"""
        try:
            surfaces = serverConfigProperty.surfaceConfigPropertyDict.values()
        except Exception:
            return

        cleaned = 0
        for surface in surfaces:
            save_dir = Path(surface.saveFolder)
            if not save_dir.exists():
                continue

            for coil_dir in save_dir.iterdir():
                if not coil_dir.is_dir():
                    continue

                old_cache_dir = coil_dir / "cache" / "area" / "tild"
                if not old_cache_dir.exists():
                    continue

                # 检查是否有旧的瓦片文件（数字_数字.jpg 格式）
                for old_file in old_cache_dir.iterdir():
                    if old_file.is_file() and old_file.suffix == ".jpg":
                        # 匹配 0_0.jpg, 1_2.jpg 等格式
                        if "_" in old_file.stem and old_file.stem.replace("_", "").isdigit():
                            try:
                                old_file.unlink()
                                cleaned += 1
                            except Exception:
                                pass

        if cleaned > 0:
            logging.info(f"Cleaned up {cleaned} old tile cache files (legacy format)")

    def startup(self) -> None:
        # 先清理旧缓存
        self.cleanup_old_cache()
        # 然后启动预加载线程
        thread = threading.Thread(target=self._prefetch_latest_tiles, name="area-tile-cache", daemon=True)
        thread.start()
