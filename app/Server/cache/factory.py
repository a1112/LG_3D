import logging
import os
import time
from typing import Optional

from .area_cache import DiskAreaImageCache
from .bounded_cache import positive_int_env
from .falsecolor_cache import FalseColorCache
from .memory_cache import Memory3dCache, MemoryImageCache
from .redis_cache import RedisImageCache


class CacheProvider:
    def __init__(self, mode: str, preview_cache, image_cache, area_cache, classifier_cache, d3_cache, falsecolor_cache=None) -> None:
        self.mode = mode
        self.preview_cache = preview_cache
        self.image_cache = image_cache
        self.area_cache = area_cache
        self.classifier_cache = classifier_cache
        self.d3_cache = d3_cache
        self.falsecolor_cache = falsecolor_cache
        self._components = [
            preview_cache,
            image_cache,
            area_cache,
            classifier_cache,
            d3_cache,
        ]
        if falsecolor_cache:
            self._components.append(falsecolor_cache)

    def startup(self) -> None:
        for component in self._components:
            if hasattr(component, "startup"):
                start_time = time.perf_counter()
                component_name = component.__class__.__name__
                logging.info("starting cache component: %s", component_name)
                component.startup()
                logging.info("started cache component: %s in %.3fs",
                             component_name,
                             time.perf_counter() - start_time)

    def shutdown(self) -> None:
        for component in reversed(self._components):
            if hasattr(component, "shutdown"):
                try:
                    component.shutdown()
                except Exception:
                    logging.exception("failed to shut down cache component: %s",
                                      component.__class__.__name__)

    def stats(self) -> dict:
        components = {
            "preview": self.preview_cache,
            "image": self.image_cache,
            "area": self.area_cache,
            "classifier": self.classifier_cache,
            "3d": self.d3_cache,
            "falsecolor": self.falsecolor_cache,
        }
        return {
            name: component.cache_stats()
            for name, component in components.items()
            if component is not None and hasattr(component, "cache_stats")
        }


def _get_cache_mode(mode: Optional[str]) -> str:
    if mode:
        return mode.lower()
    return os.getenv("IMAGE_CACHE_BACKEND", os.getenv("CACHE_BACKEND", "memory")).lower() #redis


def init_cache_provider(mode: Optional[str] = None) -> CacheProvider:
    cache_mode = _get_cache_mode(mode)
    ttl = positive_int_env("CACHE_TTL", 600)
    redis_ttl = positive_int_env("CACHE_REDIS_TTL", ttl)
    redis_host = os.getenv("CACHE_REDIS_HOST", "localhost")
    redis_port = positive_int_env("CACHE_REDIS_PORT", 6379)
    redis_db = positive_int_env("CACHE_REDIS_DB", 0, minimum=0)
    redis_password = os.getenv("CACHE_REDIS_PASSWORD")
    preview_memory_mb = positive_int_env("CACHE_PREVIEW_MAX_MB", 64)
    image_memory_mb = positive_int_env("CACHE_SOURCE_IMAGE_MAX_MB", 256)
    area_memory_mb = positive_int_env("CACHE_AREA_MAX_MB", 192)
    classifier_memory_mb = positive_int_env("CACHE_CLASSIFIER_MAX_MB", 64)
    falsecolor_memory_mb = positive_int_env("CACHE_FALSECOLOR_MAX_MB", 32)
    d3_memory_mb = positive_int_env("CACHE_3D_MAX_MB", 512)
    logging.info("init_cache_provider %s", cache_mode)
    if cache_mode == "redis":
        preview_cache = RedisImageCache(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            password=redis_password,
            cache_size=256,
            ttl=redis_ttl,
            prefix="preview",
            max_memory_mb=preview_memory_mb,
        )
        image_cache = RedisImageCache(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            password=redis_password,
            cache_size=128,
            ttl=redis_ttl,
            prefix="image",
            max_memory_mb=image_memory_mb,
        )
        area_cache = DiskAreaImageCache(32,
                                        ttl=ttl,
                                        max_memory_mb=area_memory_mb)
        classifier_cache = RedisImageCache(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            password=redis_password,
            cache_size=100,
            ttl=redis_ttl,
            prefix="classifier",
            max_memory_mb=classifier_memory_mb,
        )
    else:
        preview_cache = MemoryImageCache(512,
                                         ttl=ttl,
                                         max_memory_mb=preview_memory_mb)
        image_cache = MemoryImageCache(256,
                                       ttl=ttl,
                                       max_memory_mb=image_memory_mb)
        area_cache = DiskAreaImageCache(64,
                                        ttl=ttl,
                                        max_memory_mb=area_memory_mb)
        classifier_cache = MemoryImageCache(
            100, ttl=ttl, max_memory_mb=classifier_memory_mb)
        cache_mode = "memory"

    d3_cache = Memory3dCache(16,
                             ttl=ttl,
                             max_memory_mb=d3_memory_mb)

    # 伪彩色图像缓存
    falsecolor_cache = FalseColorCache(cache_size=64,
                                       ttl=ttl,
                                       thumbnail_size=1024,
                                       max_memory_mb=falsecolor_memory_mb)

    return CacheProvider(
        cache_mode,
        preview_cache=preview_cache,
        image_cache=image_cache,
        area_cache=area_cache,
        classifier_cache=classifier_cache,
        d3_cache=d3_cache,
        falsecolor_cache=falsecolor_cache,
    )
