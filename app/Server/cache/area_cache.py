import logging
import threading
from collections import defaultdict
from pathlib import Path
from typing import Optional

from cachetools import TTLCache, cached

from Base.CONFIG import serverConfigProperty
from .base import _resolve_image_path
from .memory_cache import MemoryImageCache


class DiskAreaImageCache(MemoryImageCache):
    """
    AREA 瓦片缓存读取类

    注意：瓦片缓存由 Alg2DServer/SaverWork 在保存 AREA 图像时生成。
    Server 端只负责读取，不再生成瓦片缓存。
    """

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

    def get_tile(self, path: str, row: int, col: int, count: int, level: int = 4) -> Optional[bytes]:
        """
        获取指定位置和级别的瓦片

        瓦片缓存由 Alg2DServer 生成，这里只读取。
        如果缓存不存在，返回 None（不再自动生成）。
        """
        if count <= 0:
            return None

        count = self.tile_count
        cache_dir = self._tile_cache_dir(path, level)

        # 从缓存读取
        tile_path = self._tile_path(cache_dir, col, row)
        if tile_path.exists():
            return tile_path.read_bytes()

        # 缓存不存在，记录日志并返回 None
        logging.debug(f"Tile cache not found: L{level} tile ({col},{row}) for {path}")
        return None

    def get_all_tiles(self, path: str, count: int) -> Optional[dict]:
        """获取所有瓦片（用于兼容旧的 clip_num 接口）"""
        if count <= 0:
            return None
        count = self.tile_count

        # 读取 L4
        cache_dir = self._tile_cache_dir(path, 4)
        return self._read_tile_cache(cache_dir, count)

    def _build_clip_cache(self):
        @cached(cache=TTLCache(maxsize=self.cache_size, ttl=self.ttl))
        def _load_image_clip(path: str, count: int) -> Optional[dict]:
            if count <= 0:
                return None
            count = self.tile_count
            return self.get_all_tiles(path, count)
        return _load_image_clip

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
        # 清理旧缓存
        self.cleanup_old_cache()
