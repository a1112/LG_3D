import io
import logging
from pathlib import Path
from typing import Optional

import numpy as np
from cachetools import TTLCache, cached

from .base import Base3dCache, BaseImageCache


class MemoryImageCache(BaseImageCache):
    """
    In-memory image cache using TTL caches (previous default behavior).
    """

    def _load_image_bytes(self, path: str) -> Optional[bytes]:
        path_obj = Path(path)
        if not path_obj.exists():
            logging.error("%s does not exist", path_obj)
            return None
        with path_obj.open("rb") as file:
            logging.debug("loading image %s", path_obj)
            return file.read()


class Memory3dCache(Base3dCache):
    def __init__(self, cache_size: int = 16, ttl: int = 200) -> None:
        self.cache_size = cache_size
        self.ttl = ttl
        self._cache = self._create_cache()

    def _create_cache(self):
        @cached(cache=TTLCache(maxsize=self.cache_size, ttl=self.ttl))
        def _load_3d_data(path: str):
            if ".npy" in str(path):
                return np.load(path).astype(int)
            return np.load(path)["array"]

        return _load_3d_data

    def get_data(self, path: str):
        try:
            return self._cache(path)
        except Exception as exc:  # pragma: no cover - defensive fallback
            logging.exception("Error loading data: %s", exc)
            return None

    def clear_cache(self) -> None:
        self._cache.cache_clear()
