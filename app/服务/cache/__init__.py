"""
Cache provider entrypoint.

Use env IMAGE_CACHE_BACKEND / CACHE_BACKEND to switch:
- memory (default): in-process TTL cache
- redis: Redis-backed cache (CACHE_REDIS_* controls connection)
"""
from typing import Tuple

from .factory import CacheProvider, init_cache_provider

# Initialize provider on import so shared singletons are ready for routers/tools.
_provider: CacheProvider = init_cache_provider()

# Backwards-compatible names
previewCache = _provider.preview_cache
imageCache = _provider.image_cache
areaCache = _provider.area_cache
classifierCache = _provider.classifier_cache
d3DataCache = _provider.d3_cache

__all__: Tuple[str, ...] = (
    "previewCache",
    "imageCache",
    "areaCache",
    "classifierCache",
    "d3DataCache",
    "cache_provider",
    "startup_cache",
    "shutdown_cache",
    "get_cache_mode",
)


def cache_provider() -> CacheProvider:
    return _provider


def get_cache_mode() -> str:
    return _provider.mode


def startup_cache() -> None:
    _provider.startup()


def shutdown_cache() -> None:
    _provider.shutdown()
