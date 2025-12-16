import io
import logging
from pathlib import Path
from typing import Optional

import numpy as np
from cachetools import TTLCache, cached

from .base import Base3dCache, BaseImageCache, _resolve_3d_path, _resolve_image_path


class MemoryImageCache(BaseImageCache):
    """
    In-memory image cache using TTL caches (previous default behavior).
    """

    def _load_image_bytes(self, path: str) -> Optional[bytes]:
        path_obj = _resolve_image_path(path)
        if not path_obj.exists():
            logging.error("%s does not exist", path_obj)
            return None
        with path_obj.open("rb") as file:
            return file.read()


class Memory3dCache(Base3dCache):
    def __init__(self, cache_size: int = 16, ttl: int = 200) -> None:
        self.cache_size = cache_size
        self.ttl = ttl
        self._cache = self._create_cache()

    def _create_cache(self):
        @cached(cache=TTLCache(maxsize=self.cache_size, ttl=self.ttl))
        def _load_3d_data(path: str):
            """
            加载 3D 数据；在开发者模式 + 本地环境下，优先从 TestData 映射路径。
            """
            # 3D 数据在开发者模式下使用固定 TestData（与 /data_has 保持一致）。
            path_obj = _resolve_3d_path(path)

            if ".npy" in str(path_obj):
                return np.load(path_obj).astype(int)
            return np.load(path_obj)["array"]

        return _load_3d_data

    def get_data(self, path: str):
        try:
            return self._cache(path)
        except Exception as exc:  # pragma: no cover - defensive fallback
            logging.exception("Error loading data: %s", exc)
            return None

    def clear_cache(self) -> None:
        self._cache.cache_clear()
