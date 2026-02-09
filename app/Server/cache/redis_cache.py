import logging
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional

import redis

from .base import BaseImageCache, _resolve_image_path

# 独立的 Redis 写入线程池，用于异步缓存写入，避免阻塞请求
_write_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="redis_write")


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
    ) -> None:
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.prefix = prefix
        self.redis_ttl = ttl
        self.client = redis.Redis(
            host=self.host,
            port=self.port,
            db=self.db,
            password=self.password,
            decode_responses=False,
        )
        super().__init__(cache_size=cache_size, ttl=ttl)

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

        _write_executor.submit(_write_to_redis)
        return binary

    def startup(self) -> None:
        try:
            self.client.ping()
        except Exception as exc:  # pragma: no cover
            logging.warning("redis cache ping failed: %s", exc)

    def shutdown(self) -> None:
        try:
            self.client.close()
        except Exception:  # pragma: no cover
            pass
        # 关闭异步写入线程池
        try:
            _write_executor.shutdown(wait=False)
        except Exception:  # pragma: no cover
            pass

    def clear_cache(self) -> None:
        super().clear_cache()
        try:
            keys = list(self.client.scan_iter(match=f"{self.prefix}:*"))
            if keys:
                self.client.delete(*keys)
        except Exception as exc:  # pragma: no cover
            logging.warning("redis cache_clear failed: %s", exc)
