import asyncio
import io
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SERVER_ROOT = PROJECT_ROOT / "app" / "Server"
for path in (PROJECT_ROOT, SERVER_ROOT, PROJECT_ROOT / "app"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from app.Server.api import ApiImageServer  # noqa: E402
from cache.area_cache import DiskAreaImageCache  # noqa: E402


class FakeDataGet:
    def __init__(self, source_type, surface_key, coil_id, type_, mask):
        self.sourceType = source_type
        self.surfaceKey = surface_key
        self.coil_id = coil_id
        self.type_ = type_
        self.mask = mask
        self.url = f"{source_type}-{surface_key}-{coil_id}-{type_}.jpg"


def _jpeg_bytes(width: int = 7, height: int = 5) -> bytes:
    image = np.arange(width * height, dtype=np.uint8).reshape(height, width)
    ok, encoded = cv2.imencode(".jpg", image)
    assert ok
    return encoded.tobytes()


def _response_image_size(response) -> tuple[int, int]:
    with Image.open(io.BytesIO(response.body)) as image:
        return image.size


def test_area_count_one_returns_full_image(monkeypatch):
    source_bytes = _jpeg_bytes()

    async def fake_get_image_async(data_get, *, pil=False, clip_num=0):
        return source_bytes

    monkeypatch.setattr(ApiImageServer, "DataGet", FakeDataGet)
    monkeypatch.setattr(ApiImageServer, "_get_image_async", fake_get_image_async)
    monkeypatch.setattr(ApiImageServer, "_schedule_prefetch", lambda *args, **kwargs: None)

    response = asyncio.run(
        ApiImageServer.get_area_tiled("S", "1", row=0, col=0, count=1, level=4)
    )

    assert response.media_type == "image/jpeg"
    assert _response_image_size(response) == (7, 5)


def test_area_fallback_tile_uses_row_col_and_keeps_last_edge(monkeypatch):
    source_bytes = _jpeg_bytes(width=7, height=5)

    async def fake_get_image_async(data_get, *, pil=False, clip_num=0):
        if clip_num:
            return None
        return source_bytes

    monkeypatch.setattr(ApiImageServer, "DataGet", FakeDataGet)
    monkeypatch.setattr(ApiImageServer.areaCache, "get_tile", lambda *args, **kwargs: None)
    monkeypatch.setattr(ApiImageServer, "_get_image_async", fake_get_image_async)
    monkeypatch.setattr(ApiImageServer, "_schedule_prefetch", lambda *args, **kwargs: None)

    response = asyncio.run(
        ApiImageServer.get_area_tiled("S", "1", row=2, col=1, count=3, level=4)
    )

    assert response.headers["X-Cache"] == "fallback"
    assert _response_image_size(response) == (2, 3)


def test_image_api_thread_worker_setting_is_bounded(monkeypatch):
    monkeypatch.delenv("IMAGE_API_THREAD_POOL_WORKERS", raising=False)
    default_workers = ApiImageServer._get_image_api_thread_workers()
    assert 4 <= default_workers <= 16

    monkeypatch.setenv("IMAGE_API_THREAD_POOL_WORKERS", "0")
    assert ApiImageServer._get_image_api_thread_workers() == 1

    monkeypatch.setenv("IMAGE_API_THREAD_POOL_WORKERS", "999")
    assert ApiImageServer._get_image_api_thread_workers() == 64

    monkeypatch.setenv("IMAGE_API_THREAD_POOL_WORKERS", "bad")
    assert ApiImageServer._get_image_api_thread_workers() == default_workers


def test_area_cache_read_failure_returns_none(tmp_path):
    cache = DiskAreaImageCache()

    assert cache._read_tile_bytes(tmp_path / "missing.jpg") is None
