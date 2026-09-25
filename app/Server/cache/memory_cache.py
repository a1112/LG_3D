import io
import logging
import threading
from pathlib import Path
from typing import Optional

import numpy as np

from .base import Base3dCache, BaseImageCache, _resolve_3d_path, _resolve_image_path
from .bounded_cache import (MemoryBoundedTTLCache, memory_budget_bytes,
                            singleflight_cached)


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
    def __init__(self,
                 cache_size: int = 16,
                 ttl: int = 200,
                 max_memory_mb: Optional[int] = None) -> None:
        self.cache_size = cache_size
        self.ttl = ttl
        if max_memory_mb is None:
            self.max_memory_bytes = memory_budget_bytes("CACHE_3D_MAX_MB", 512)
        else:
            self.max_memory_bytes = max(int(max_memory_mb), 1) * 1024 * 1024
        self._cache = self._create_cache()

    def _create_cache(self):
        cache = MemoryBoundedTTLCache(max_bytes=self.max_memory_bytes,
                                      max_entries=self.cache_size,
                                      ttl=self.ttl)
        def _load_3d_data(path: str):
            """
            加载 3D 数据；在开发者模式 + 本地环境下，优先从 TestData 映射路径。
            """
            # 3D 数据在开发者模式下使用固定 TestData（与 /data_has 保持一致）。
            path_obj = _resolve_3d_path(path)

            if path_obj.suffix.lower() == ".npy":
                return np.load(path_obj, allow_pickle=False).astype(int)
            # Explicitly close NpzFile.  Depending on garbage collection for
            # closure can retain file handles during sustained API traffic.
            with np.load(path_obj, allow_pickle=False) as archive:
                return archive["array"]

        cached_loader = singleflight_cached(cache)(_load_3d_data)

        def _load_3d_data_cached(path: str):
            normalized_path = str(Path(path).resolve())
            return cached_loader(normalized_path)

        _load_3d_data_cached.cache = cache
        _load_3d_data_cached.cache_clear = cached_loader.cache_clear
        _load_3d_data_cached.cache_lock = cached_loader.cache_lock
        return _load_3d_data_cached

    def get_data(self, path: str):
        try:
            return self._cache(path)
        except Exception as exc:  # pragma: no cover - defensive fallback
            logging.exception("Error loading data: %s", exc)
            return None

    def clear_cache(self) -> None:
        self._cache.cache_clear()

    def shutdown(self) -> None:
        self.clear_cache()

    def cache_stats(self) -> dict:
        cache = self._cache.cache
        return {
            "entries": len(cache),
            "bytes": cache.currsize,
            "maxBytes": cache.maxsize,
            "maxEntries": cache.max_entries,
        }
