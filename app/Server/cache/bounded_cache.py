"""Memory-aware cache primitives used by the API image service.

``cachetools`` limits caches by item count unless a ``getsizeof`` callback is
provided.  Images and 3-D arrays vary by several orders of magnitude, so an
item-count-only cache can retain multiple gigabytes while still appearing to
be within its configured limit.
"""

import os
import threading
from collections.abc import Mapping
from functools import update_wrapper
from typing import Any

import numpy as np
from PIL import Image
from cachetools import TTLCache
from cachetools.keys import hashkey


_MIN_VALUE_SIZE = 256


def positive_int_env(name: str, default: int, minimum: int = 1) -> int:
    """Read a positive integer environment setting with a safe fallback."""
    raw_value = os.getenv(name)
    if raw_value is None:
        return max(default, minimum)
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        return max(default, minimum)
    return max(value, minimum)


def memory_budget_bytes(env_name: str, default_mb: int) -> int:
    """Return an environment-controlled memory budget in bytes."""
    return positive_int_env(env_name, default_mb) * 1024 * 1024


def estimate_value_size(value: Any) -> int:
    """Estimate retained payload memory without copying image/array data."""
    if value is None:
        return _MIN_VALUE_SIZE
    if isinstance(value, (bytes, bytearray, memoryview)):
        return max(len(value), _MIN_VALUE_SIZE)
    if isinstance(value, np.ndarray):
        return max(int(value.nbytes), _MIN_VALUE_SIZE)
    if isinstance(value, Image.Image):
        bands = max(len(value.getbands()), 1)
        return max(int(value.width) * int(value.height) * bands,
                   _MIN_VALUE_SIZE)
    if isinstance(value, Mapping):
        total = _MIN_VALUE_SIZE
        for key, item in value.items():
            total += estimate_value_size(key)
            total += estimate_value_size(item)
        return total
    if isinstance(value, (tuple, list, set, frozenset)):
        return _MIN_VALUE_SIZE + sum(estimate_value_size(item)
                                     for item in value)
    return _MIN_VALUE_SIZE


class MemoryBoundedTTLCache(TTLCache):
    """TTL cache bounded by both retained bytes and number of entries."""

    def __init__(self, *, max_bytes: int, max_entries: int, ttl: int) -> None:
        super().__init__(maxsize=max(int(max_bytes), 1),
                         ttl=max(int(ttl), 1),
                         getsizeof=estimate_value_size)
        self.max_entries = max(int(max_entries), 1)

    def __setitem__(self, key, value) -> None:
        # TTLCache raises ValueError for a value larger than maxsize.  The
        # cachetools decorator handles that by returning the uncached value.
        super().__setitem__(key, value)
        while len(self) > self.max_entries:
            self.popitem()


def singleflight_cached(cache: MemoryBoundedTTLCache,
                        wait_timeout: int | None = None):
    """Cache decorator that coalesces concurrent misses for the same key."""
    if wait_timeout is None:
        wait_timeout = positive_int_env("CACHE_SINGLEFLIGHT_WAIT_TIMEOUT", 60)
    cache_lock = threading.RLock()
    pending: dict[tuple, threading.Event] = {}

    def decorator(function):
        def wrapper(*args, **kwargs):
            key = hashkey(*args, **kwargs)
            while True:
                with cache_lock:
                    try:
                        return cache[key]
                    except KeyError:
                        event = pending.get(key)
                        if event is None:
                            event = threading.Event()
                            pending[key] = event
                            leader = True
                        else:
                            leader = False
                if leader:
                    break
                if not event.wait(timeout=wait_timeout):
                    raise TimeoutError(
                        f"cache singleflight wait exceeded {wait_timeout}s")

            try:
                value = function(*args, **kwargs)
                with cache_lock:
                    try:
                        cache[key] = value
                    except ValueError:
                        pass
                return value
            finally:
                with cache_lock:
                    pending.pop(key, None)
                    event.set()

        def cache_clear() -> None:
            with cache_lock:
                cache.clear()

        wrapper.cache = cache
        wrapper.cache_lock = cache_lock
        wrapper.cache_clear = cache_clear
        wrapper.cache_info = None
        return update_wrapper(wrapper, function)

    return decorator
