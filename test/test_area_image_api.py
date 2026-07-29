import asyncio
import io
import json
import os
import sys
import threading
import time
from pathlib import Path

import cv2
import httpx
import numpy as np
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SERVER_ROOT = PROJECT_ROOT / "app" / "Server"
for path in (PROJECT_ROOT, SERVER_ROOT, PROJECT_ROOT / "app"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from app.Server.api import ApiImageServer  # noqa: E402
from app.Server.api import api_core  # noqa: E402
from cache.area_cache import DiskAreaImageCache  # noqa: E402
from cache.area_tile_builder import rebuild_area_tile_cache  # noqa: E402
from cache.memory_cache import MemoryImageCache  # noqa: E402


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


def _write_jpeg(path: Path, width: int, height: int) -> None:
    image = np.arange(width * height, dtype=np.uint8).reshape(height, width)
    ok, encoded = cv2.imencode(".jpg", image)
    assert ok
    path.write_bytes(encoded.tobytes())


def test_area_count_one_returns_full_image(monkeypatch):
    source_bytes = _jpeg_bytes()

    async def fake_get_image_async(data_get, *, pil=False, clip_num=0):
        return source_bytes

    monkeypatch.setattr(ApiImageServer, "DataGet", FakeDataGet)
    monkeypatch.setattr(ApiImageServer, "_get_image_async",
                        fake_get_image_async)
    monkeypatch.setattr(ApiImageServer, "_schedule_prefetch",
                        lambda *args, **kwargs: None)

    response = asyncio.run(
        ApiImageServer.get_area_tiled("S", "1", row=0, col=0, count=1,
                                      level=4))

    assert response.media_type == "image/jpeg"
    assert _response_image_size(response) == (7, 5)


def test_preview_image_uses_cache_loader(monkeypatch):
    source_bytes = _jpeg_bytes()
    seen = {}

    async def fake_get_image_async(data_get, *, pil=False, clip_num=0):
        seen["source_type"] = data_get.sourceType
        seen["type"] = data_get.type_
        return source_bytes

    monkeypatch.setattr(ApiImageServer, "DataGet", FakeDataGet)
    monkeypatch.setattr(ApiImageServer, "_get_image_async",
                        fake_get_image_async)
    monkeypatch.setattr(ApiImageServer, "_schedule_prefetch",
                        lambda *args, **kwargs: None)

    response = asyncio.run(ApiImageServer.get_preview_image("S", "1", "JET"))

    assert response.media_type == "image/jpeg"
    assert response.body == source_bytes
    assert response.headers["cache-control"] == "public, max-age=600"
    assert seen == {"source_type": "preview", "type": "JET"}


def test_source_thumbnail_reuses_preview_response(monkeypatch):
    expected = object()
    seen = {}

    async def fake_get_preview_image(surface_key, coil_id, type_, mask=False):
        seen.update({
            "surface_key": surface_key,
            "coil_id": coil_id,
            "type": type_,
            "mask": mask,
        })
        return expected

    monkeypatch.setattr(ApiImageServer, "get_preview_image",
                        fake_get_preview_image)

    response = asyncio.run(
        ApiImageServer.get_image("L",
                                 "211954",
                                 "GRAY",
                                 mask=True,
                                 thumbnail=True))

    assert response is expected
    assert seen == {
        "surface_key": "L",
        "coil_id": "211954",
        "type": "GRAY",
        "mask": True,
    }


def test_area_mask_route_uses_requested_type(monkeypatch):
    source_bytes = _jpeg_bytes()
    seen = {}

    async def fake_get_image_async(data_get, *, pil=False, clip_num=0):
        seen["type"] = data_get.type_
        return source_bytes

    monkeypatch.setattr(ApiImageServer, "DataGet", FakeDataGet)
    monkeypatch.setattr(ApiImageServer, "_get_image_async",
                        fake_get_image_async)
    monkeypatch.setattr(ApiImageServer, "_schedule_prefetch",
                        lambda *args, **kwargs: None)

    response = asyncio.run(
        ApiImageServer.get_area_tiled("S",
                                      "1",
                                      "AREA_MASK",
                                      row=0,
                                      col=0,
                                      count=1,
                                      level=4))

    assert response.media_type == "image/jpeg"
    assert seen["type"] == "AREA_MASK"


def test_area_fallback_tile_uses_row_col_and_keeps_last_edge(monkeypatch):
    source_bytes = _jpeg_bytes(width=7, height=5)

    async def fake_get_image_async(data_get, *, pil=False, clip_num=0):
        if clip_num:
            return None
        return source_bytes

    monkeypatch.setattr(ApiImageServer, "DataGet", FakeDataGet)
    monkeypatch.setattr(ApiImageServer.areaCache, "get_tile",
                        lambda *args, **kwargs: None)
    monkeypatch.setattr(ApiImageServer, "_get_image_async",
                        fake_get_image_async)
    monkeypatch.setattr(ApiImageServer, "_schedule_prefetch",
                        lambda *args, **kwargs: None)

    response = asyncio.run(
        ApiImageServer.get_area_tiled("S", "1", row=2, col=1, count=3,
                                      level=4))

    assert response.headers["X-Cache"] == "fallback"
    assert _response_image_size(response) == (2, 3)


def test_area_tile_disk_stall_does_not_block_health(monkeypatch):
    entered = threading.Event()
    release = threading.Event()

    def blocked_get_tile(*args, **kwargs):
        entered.set()
        release.wait(timeout=2)
        return _jpeg_bytes(width=2, height=2)

    monkeypatch.setattr(ApiImageServer, "DataGet", FakeDataGet)
    monkeypatch.setattr(ApiImageServer.areaCache, "get_tile", blocked_get_tile)
    monkeypatch.setattr(ApiImageServer, "_schedule_prefetch",
                        lambda *args, **kwargs: None)

    async def exercise():
        transport = httpx.ASGITransport(app=ApiImageServer.app)
        async with httpx.AsyncClient(transport=transport,
                                     base_url="http://test") as client:
            tile_request = asyncio.create_task(
                client.get("/image/area/S/1?row=0&col=0&count=3&level=4"))
            assert await asyncio.to_thread(entered.wait, 1)

            started = time.monotonic()
            health_response = await asyncio.wait_for(client.get("/health"),
                                                     timeout=0.5)
            elapsed = time.monotonic() - started
            release.set()
            tile_response = await tile_request
            return health_response, tile_response, elapsed

    try:
        health_response, tile_response, elapsed = asyncio.run(exercise())
    finally:
        release.set()

    assert health_response.status_code == 200
    assert tile_response.status_code == 200
    assert tile_response.headers["X-Cache"] == "hit"
    assert elapsed < 0.5


def test_health_reports_exhausted_stalled_image_workers(monkeypatch):
    monkeypatch.setattr(ApiImageServer, "_IMAGE_THREAD_WORKERS", 2)
    monkeypatch.setattr(ApiImageServer, "_IMAGE_HEALTH_STALL_SECONDS", 1.0)
    old_started_at = time.monotonic() - 10
    with ApiImageServer._image_operations_lock:
        ApiImageServer._image_operations.clear()
        ApiImageServer._image_operations.update({
            1: {
                "submitted_at": old_started_at,
                "started_at": old_started_at,
            },
            2: {
                "submitted_at": old_started_at,
                "started_at": old_started_at,
            },
        })

    try:
        response = asyncio.run(api_core.health())
    finally:
        with ApiImageServer._image_operations_lock:
            ApiImageServer._image_operations.clear()

    assert response.status_code == 503
    payload = json.loads(response.body)
    assert payload["ok"] is False
    assert payload["imageExecutor"]["stalledWorkers"] == 2


def test_area_clip_cache_uses_row_col_and_keeps_last_edge(tmp_path):
    image_path = tmp_path / "AREA.jpg"
    _write_jpeg(image_path, width=7, height=5)
    cache = MemoryImageCache()

    image_dict = cache.get_image(str(image_path), clip_num=3)
    assert image_dict is not None

    with Image.open(io.BytesIO(image_dict[1][2])) as tile:
        assert tile.size == (2, 3)


def test_area_count_zero_prefers_real_source_size_over_tile_cache(
        monkeypatch, tmp_path):
    coil_dir = tmp_path / "205941"
    image_path = coil_dir / "jpg" / "AREA.jpg"
    image_path.parent.mkdir(parents=True)
    _write_jpeg(image_path, width=7, height=5)

    cache_dir = coil_dir / "cache" / "area" / "tild" / "L4"
    cache_dir.mkdir(parents=True)
    _write_jpeg(cache_dir / "0_0.jpg", width=2, height=1)

    class PathDataGet(FakeDataGet):

        def __init__(self, source_type, surface_key, coil_id, type_, mask):
            super().__init__(source_type, surface_key, coil_id, type_, mask)
            self.url = str(image_path)

    monkeypatch.setattr(ApiImageServer, "DataGet", PathDataGet)
    monkeypatch.setattr(ApiImageServer, "_schedule_prefetch",
                        lambda *args, **kwargs: None)

    response = asyncio.run(
        ApiImageServer.get_area_tiled("S",
                                      "205941",
                                      row=0,
                                      col=0,
                                      count=0,
                                      level=4))

    assert response == {"width": 7, "height": 5}


def test_rebuild_area_tile_cache_removes_old_tiles_and_writes_current_strategy(
        tmp_path):
    coil_dir = tmp_path / "205941"
    image_path = coil_dir / "jpg" / "AREA.jpg"
    image_path.parent.mkdir(parents=True)
    _write_jpeg(image_path, width=7, height=5)

    old_cache_dir = coil_dir / "cache" / "area" / "tild"
    old_cache_dir.mkdir(parents=True)
    (old_cache_dir / "0_0.jpg").write_bytes(b"old")
    (old_cache_dir / "L0").mkdir()
    (old_cache_dir / "L0" / "0_0.jpg").write_bytes(b"old-l0")

    result = rebuild_area_tile_cache(image_path)

    assert result.rebuilt
    assert result.removed_files == 2
    assert result.tiles == 45
    assert not (old_cache_dir / "0_0.jpg").exists()
    assert len(list((old_cache_dir / "L0").glob("*.jpg"))) == 9
    assert len(list((old_cache_dir / "L4").glob("*.jpg"))) == 9
    with Image.open(old_cache_dir / "L4" / "2_2.jpg") as tile:
        assert tile.size == (3, 3)


def test_rebuild_area_tile_cache_api_clears_area_cache(monkeypatch, tmp_path):
    image_path = tmp_path / "205941" / "jpg" / "AREA.jpg"
    image_path.parent.mkdir(parents=True)
    _write_jpeg(image_path, width=7, height=5)
    cleared = {}

    class PathDataGet(FakeDataGet):

        def __init__(self, source_type, surface_key, coil_id, type_, mask):
            super().__init__(source_type, surface_key, coil_id, type_, mask)
            self.url = str(image_path)

    monkeypatch.setattr(ApiImageServer, "DataGet", PathDataGet)
    monkeypatch.setattr(ApiImageServer.areaCache, "clear_cache",
                        lambda: cleared.setdefault("ok", True))

    response = asyncio.run(
        ApiImageServer.rebuild_area_tile_cache_api("S", "205941", "AREA"))

    assert response["ok"] is True
    assert response["surface_key"] == "S"
    assert response["coil_id"] == "205941"
    assert response["type"] == "AREA"
    assert cleared == {"ok": True}


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


def test_area_cache_rejects_tile_older_than_source(tmp_path):
    cache = DiskAreaImageCache()
    coil_dir = tmp_path / "205941"
    image_path = coil_dir / "jpg" / "AREA.jpg"
    image_path.parent.mkdir(parents=True)
    _write_jpeg(image_path, width=7, height=5)

    tile_path = coil_dir / "cache" / "area" / "tild" / "L4" / "0_0.jpg"
    tile_path.parent.mkdir(parents=True)
    tile_path.write_bytes(b"stale")
    source_time = image_path.stat().st_mtime_ns
    os.utime(tile_path, ns=(source_time - 1, source_time - 1))

    assert cache.get_tile(str(image_path), row=0, col=0, count=3,
                          level=4) is None

    os.utime(tile_path, ns=(source_time + 1, source_time + 1))
    assert cache.get_tile(str(image_path), row=0, col=0, count=3,
                          level=4) == b"stale"


def test_area_mask_uses_separate_tile_cache_dir(tmp_path):
    cache = DiskAreaImageCache()
    coil_dir = tmp_path / "205941"
    area_path = coil_dir / "jpg" / "AREA.jpg"
    mask_path = coil_dir / "jpg" / "AREA_MASK.jpg"

    assert cache._tile_cache_base_dir(
        str(area_path)) == coil_dir / "cache" / "area" / "tild"
    assert cache._tile_cache_base_dir(
        str(mask_path)) == coil_dir / "cache" / "area" / "AREA_MASK" / "tild"
