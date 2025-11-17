import logging
from pathlib import Path
from typing import Optional

import redis

from .base import BaseImageCache


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
        key = self._key(path)
        try:
            cached_bytes = self.client.get(key)
            if cached_bytes:
                return cached_bytes
        except Exception as exc:  # pragma: no cover - best-effort for Redis failures
            logging.warning("redis get failed for %s: %s", key, exc)

        path_obj = Path(path)
        if not path_obj.exists():
            logging.error("%s does not exist", path_obj)
            return None

        binary = path_obj.read_bytes()
        try:
            self.client.setex(key, self.redis_ttl, binary)
        except Exception as exc:  # pragma: no cover
            logging.warning("redis setex failed for %s: %s", key, exc)
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

    def clear_cache(self) -> None:
        super().clear_cache()
        try:
            keys = list(self.client.scan_iter(match=f"{self.prefix}:*"))
            if keys:
                self.client.delete(*keys)
        except Exception as exc:  # pragma: no cover
            logging.warning("redis cache_clear failed: %s", exc)
