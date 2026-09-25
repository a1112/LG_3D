import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional

import redis

from .base import BaseImageCache, _resolve_image_path
from .bounded_cache import positive_int_env

# 独立的 Redis 写入线程池，用于异步缓存写入，避免阻塞请求
class _BoundedWriteExecutor:
    """Drop best-effort writes instead of retaining an unbounded image queue."""

    def __init__(self) -> None:
        workers = positive_int_env("CACHE_REDIS_WRITE_WORKERS", 2)
        pending = positive_int_env("CACHE_REDIS_WRITE_PENDING", 2)
        self._executor = ThreadPoolExecutor(max_workers=workers,
                                            thread_name_prefix="redis_write")
        self._slots = threading.BoundedSemaphore(workers + pending)
        self._shutdown_lock = threading.Lock()
        self._shutdown = False

    def submit(self, function) -> bool:
        if not self._slots.acquire(blocking=False):
            return False
        with self._shutdown_lock:
            if self._shutdown:
                self._slots.release()
                return False
            try:
                future = self._executor.submit(function)
            except RuntimeError:
                self._slots.release()
                return False
        future.add_done_callback(lambda _future: self._slots.release())
        return True

    def shutdown(self) -> None:
        with self._shutdown_lock:
            if self._shutdown:
                return
            self._shutdown = True
        self._executor.shutdown(wait=False, cancel_futures=True)


_write_executor = _BoundedWriteExecutor()


class RedisImageCache(BaseImageCache):
    """
    Redis-backed image cache. Falls back to local file reads when Redis misses or is unavailable.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        cache_size: int = 128,
        ttl: int = 200,
        prefix: str = "image-cache",
        max_memory_mb: Optional[int] = None,
    ) -> None:
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.prefix = prefix
        self.redis_ttl = ttl
        self.max_redis_value_bytes = positive_int_env(
            "CACHE_REDIS_MAX_VALUE_MB", 32) * 1024 * 1024
        self.client = redis.Redis(
            host=self.host,
            port=self.port,
            db=self.db,
            password=self.password,
            socket_connect_timeout=0.5,
            socket_timeout=0.5,
            health_check_interval=30,
            decode_responses=False,
        )
        super().__init__(cache_size=cache_size,
                         ttl=ttl,
                         max_memory_mb=max_memory_mb)

    def _key(self, path: str) -> str:
        return f"{self.prefix}:{path}"

    def _load_image_bytes(self, path: str) -> Optional[bytes]:
        logging.debug("redis loading image from %s", path)
        key = self._key(path)
        try:
            sT=time.time()
            cached_bytes = self.client.get(key)
            logging.debug("redis loading image %s time: %.3fs", path, time.time()-sT)
            if cached_bytes:
                return cached_bytes
        except Exception as exc:  # pragma: no cover - best-effort for Redis failures
            logging.warning("redis get failed for %s: %s", key, exc)

        path_obj = _resolve_image_path(path)
        if not path_obj.exists():
            logging.error("%s does not exist", path_obj)
            return None
        sT=time.time()
        binary = path_obj.read_bytes()
        logging.debug("io loading image %s time: %.3fs", path, time.time()-sT)

        # 异步写入 Redis，不阻塞当前请求响应
        def _write_to_redis():
            try:
                self.client.setex(key, self.redis_ttl, binary)
            except Exception as exc:
                logging.warning("redis setex failed for %s: %s", key, exc)

        if len(binary) <= self.max_redis_value_bytes:
            if not _write_executor.submit(_write_to_redis):
                logging.debug("redis write queue full, skip %s", key)
        else:
            logging.debug("redis value too large, skip %s bytes=%s", key,
                          len(binary))
        return binary

    def startup(self) -> None:
        try:
            self.client.ping()
        except Exception as exc:  # pragma: no cover
            logging.warning("redis cache ping failed: %s", exc)

    def shutdown(self) -> None:
        # Clear only process-local decoded/raw caches.  Do not delete shared
        # Redis keys during a normal service shutdown.
        BaseImageCache.clear_cache(self)
        try:
            self.client.close()
        except Exception as exc:  # pragma: no cover
            logging.debug("redis cache close failed: %s", exc)
        # 关闭异步写入线程池
        try:
            _write_executor.shutdown()
        except Exception as exc:  # pragma: no cover
            logging.debug("redis cache write executor shutdown failed: %s", exc)

    def clear_cache(self) -> None:
        super().clear_cache()
        try:
            batch = []
            for key in self.client.scan_iter(match=f"{self.prefix}:*",
                                              count=500):
                batch.append(key)
                if len(batch) >= 500:
                    self.client.delete(*batch)
                    batch.clear()
            if batch:
                self.client.delete(*batch)
        except Exception as exc:  # pragma: no cover
            logging.warning("redis cache_clear failed: %s", exc)
