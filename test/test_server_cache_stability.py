import asyncio
import concurrent.futures
import sys
import threading
import time
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SERVER_ROOT = PROJECT_ROOT / "app" / "Server"
for path in (PROJECT_ROOT, SERVER_ROOT, PROJECT_ROOT / "app"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from app.Server.api import ApiImageServer, ApiTest  # noqa: E402
from fastapi import HTTPException  # noqa: E402
from cache.bounded_cache import (MemoryBoundedTTLCache,  # noqa: E402
                                 singleflight_cached)
from cache.memory_cache import Memory3dCache, MemoryImageCache  # noqa: E402
from cache.falsecolor_cache import FalseColorCache  # noqa: E402
from cache.redis_cache import RedisImageCache  # noqa: E402


def test_memory_bounded_ttl_cache_enforces_bytes_and_entries():
    byte_cache = MemoryBoundedTTLCache(max_bytes=700,
                                       max_entries=10,
                                       ttl=60)
    byte_cache["first"] = b"a" * 400
    byte_cache["second"] = b"b" * 400
    assert list(byte_cache) == ["second"]
    assert byte_cache.currsize <= 700

    entry_cache = MemoryBoundedTTLCache(max_bytes=4096,
                                        max_entries=2,
                                        ttl=60)
    entry_cache["first"] = b"a"
    entry_cache["second"] = b"b"
    entry_cache["third"] = b"c"
    assert len(entry_cache) == 2
    assert "first" not in entry_cache


def test_singleflight_cache_coalesces_concurrent_misses():
    cache = MemoryBoundedTTLCache(max_bytes=4096,
                                  max_entries=4,
                                  ttl=60)
    calls = 0
    calls_lock = threading.Lock()

    @singleflight_cached(cache)
    def load(key):
        nonlocal calls
        with calls_lock:
            calls += 1
        time.sleep(0.05)
        return b"value"

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(load, ["same"] * 8))

    assert results == [b"value"] * 8
    assert calls == 1


def test_singleflight_follower_has_finite_wait():
    cache = MemoryBoundedTTLCache(max_bytes=4096,
                                  max_entries=4,
                                  ttl=60)
    entered = threading.Event()
    release = threading.Event()

    @singleflight_cached(cache, wait_timeout=0.05)
    def load(key):
        entered.set()
        release.wait(timeout=2)
        return b"value"

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        leader = executor.submit(load, "same")
        assert entered.wait(timeout=1)
        started = time.monotonic()
        try:
            load("same")
            assert False, "singleflight follower should time out"
        except TimeoutError:
            elapsed = time.monotonic() - started
        finally:
            release.set()
        assert leader.result(timeout=1) == b"value"

    assert elapsed < 0.5


def test_image_cache_clear_and_shutdown_release_all_layers(tmp_path):
    image_path = tmp_path / "image.jpg"
    image_path.write_bytes(b"not-a-real-image")
    cache = MemoryImageCache(cache_size=4, ttl=60, max_memory_mb=4)

    assert cache.get_image(str(image_path)) == b"not-a-real-image"
    assert len(cache._cache_image_byte.cache) == 1
    stats = cache.cache_stats()
    assert stats["entries"] == 1
    assert stats["bytes"] <= stats["maxBytes"]

    cache.shutdown()

    assert len(cache._cache_image_byte.cache) == 0
    assert len(cache._cache_image_pil.cache) == 0
    assert len(cache._cache_image_clip.cache) == 0
    assert len(cache._mask_cache_image_byte.cache) == 0


def test_oversized_3d_value_is_returned_but_not_retained(tmp_path):
    data_path = tmp_path / "3D.npy"
    expected = np.arange(400_000, dtype=np.int32)
    np.save(data_path, expected)
    cache = Memory3dCache(cache_size=4, ttl=60, max_memory_mb=1)

    result = cache.get_data(str(data_path))

    assert np.array_equal(result, expected)
    assert len(cache._cache.cache) == 0


class _StreamingUpload:
    filename = "speed.bin"

    def __init__(self, chunks):
        self._chunks = iter(chunks)
        self.read_sizes = []

    async def read(self, size=-1):
        self.read_sizes.append(size)
        return next(self._chunks, b"")


def test_speedtest_upload_reads_in_bounded_chunks():
    upload = _StreamingUpload([b"a" * 10, b"b" * 20])

    result = asyncio.run(ApiTest.upload_test(upload))

    assert result["filename"] == "speed.bin"
    assert upload.read_sizes == [1024 * 1024] * 3


def test_defect_crop_rejects_dimensions_that_could_exhaust_memory(
        monkeypatch):
    monkeypatch.setattr(ApiImageServer, "_DEFECT_CROP_MAX_DIMENSION", 1000)
    monkeypatch.setattr(ApiImageServer, "_DEFECT_CROP_MAX_PIXELS", 10000)

    try:
        asyncio.run(
            ApiImageServer.get_defect_image("S", 1, "GRAY", "0", "0",
                                            "1000000", "1000000"))
    except HTTPException as exc:
        assert exc.status_code == 413
    else:
        raise AssertionError("oversized crop must be rejected before allocation")


def test_redis_clear_cache_deletes_keys_in_fixed_batches():
    class FakeRedis:
        def __init__(self):
            self.deleted_sizes = []
            self.scan_count = None

        def scan_iter(self, *, match, count):
            assert match == "test:*"
            self.scan_count = count
            yield from (f"key-{index}".encode() for index in range(1201))

        def delete(self, *keys):
            self.deleted_sizes.append(len(keys))

    cache = RedisImageCache(prefix="test", cache_size=2, max_memory_mb=1)
    fake_redis = FakeRedis()
    cache.client = fake_redis

    cache.clear_cache()

    assert fake_redis.scan_count == 500
    assert fake_redis.deleted_sizes == [500, 500, 201]


def test_falsecolor_cache_lock_has_finite_wait(monkeypatch):
    cache = FalseColorCache(cache_size=1,
                            ttl=60,
                            max_memory_mb=1,
                            lock_timeout=0.02)
    monkeypatch.setattr(cache, "get_thumbnail", lambda *args: None)

    def fail_generation(*args, **kwargs):
        raise AssertionError("lock waiter must not start generation")

    monkeypatch.setattr(cache, "generate_thumbnail", fail_generation)
    cache._lock.acquire()
    try:
        started = time.monotonic()
        result = cache.get_or_generate("blocked.npy",
                                       np.zeros((2, 2), dtype=np.uint8))
        elapsed = time.monotonic() - started
    finally:
        cache._lock.release()

    assert result == (None, False)
    assert elapsed < 0.5
