import os
from typing import Optional

from .area_cache import DiskAreaImageCache
from .memory_cache import Memory3dCache, MemoryImageCache
from .redis_cache import RedisImageCache


class CacheProvider:
    def __init__(self, mode: str, preview_cache, image_cache, area_cache, classifier_cache, d3_cache) -> None:
        self.mode = mode
        self.preview_cache = preview_cache
        self.image_cache = image_cache
        self.area_cache = area_cache
        self.classifier_cache = classifier_cache
        self.d3_cache = d3_cache
        self._components = [
            preview_cache,
            image_cache,
            area_cache,
            classifier_cache,
            d3_cache,
        ]

    def startup(self) -> None:
        for component in self._components:
            if hasattr(component, "startup"):
                component.startup()

    def shutdown(self) -> None:
        for component in self._components:
            if hasattr(component, "shutdown"):
                component.shutdown()


def _get_cache_mode(mode: Optional[str]) -> str:
    if mode:
        return mode.lower()
    return os.getenv("IMAGE_CACHE_BACKEND", os.getenv("CACHE_BACKEND", "memory")).lower() #redis


def init_cache_provider(mode: Optional[str] = None) -> CacheProvider:
    cache_mode = _get_cache_mode(mode)
    ttl = int(os.getenv("CACHE_TTL", "60"))
    redis_ttl = int(os.getenv("CACHE_REDIS_TTL", str(ttl)))
    redis_host = os.getenv("CACHE_REDIS_HOST", "localhost")
    redis_port = int(os.getenv("CACHE_REDIS_PORT", "6379"))
    redis_db = int(os.getenv("CACHE_REDIS_DB", "0"))
    redis_password = os.getenv("CACHE_REDIS_PASSWORD")
    print(fr"init_cache_provider {cache_mode}")
    if cache_mode == "redis":
        preview_cache = RedisImageCache(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            password=redis_password,
            cache_size=256,
            ttl=redis_ttl,
            prefix="preview",
        )
        image_cache = RedisImageCache(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            password=redis_password,
            cache_size=128,
            ttl=redis_ttl,
            prefix="image",
        )
        area_cache = DiskAreaImageCache(32, ttl=ttl)
        classifier_cache = RedisImageCache(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            password=redis_password,
            cache_size=100,
            ttl=redis_ttl,
            prefix="classifier",
        )
    else:
        preview_cache = MemoryImageCache(256, ttl=ttl)
        image_cache = MemoryImageCache(128, ttl=ttl)
        area_cache = DiskAreaImageCache(32, ttl=ttl)
        classifier_cache = MemoryImageCache(100, ttl=ttl)
        cache_mode = "memory"

    d3_cache = Memory3dCache(16, ttl=ttl)

    return CacheProvider(
        cache_mode,
        preview_cache=preview_cache,
        image_cache=image_cache,
        area_cache=area_cache,
        classifier_cache=classifier_cache,
        d3_cache=d3_cache,
    )
