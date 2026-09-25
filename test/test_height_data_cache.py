import concurrent.futures
import sys
import threading
from pathlib import Path

import numpy as np
import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SERVER_ROOT = PROJECT_ROOT / "app" / "Server"
for path in (PROJECT_ROOT, SERVER_ROOT, PROJECT_ROOT / "app"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from app.Server.api import ApiDataServer  # noqa: E402


class _FakeDataGet:
    def __init__(self, *_args, **_kwargs):
        pass

    def get_image(self, pil=False):
        return np.ones((8, 8), dtype=np.uint8)

    def get_3d_data(self):
        return np.ones((8, 8), dtype=np.int32)


@pytest.fixture(autouse=True)
def _clear_height_data_cache():
    ApiDataServer._get_height_data_sync.cache_clear()
    yield
    ApiDataServer._get_height_data_sync.cache_clear()


def test_height_data_same_key_concurrent_requests_compute_once(monkeypatch):
    calls = 0
    calls_lock = threading.Lock()
    calculation_started = threading.Event()
    release_calculation = threading.Event()

    class BlockingLineData:
        def __init__(self, _data, _mask, point_l, point_r):
            nonlocal calls
            with calls_lock:
                calls += 1
            self.point_l = point_l
            self.point_r = point_r
            calculation_started.set()
            assert release_calculation.wait(timeout=2)

        def split_image_line_points(self, ray=False):
            assert ray is False
            return [[
                [self.point_l.x, self.point_l.y, 100],
                [self.point_r.x, self.point_r.y, 200],
            ]]

    monkeypatch.setattr(ApiDataServer, "DataGet", _FakeDataGet)
    monkeypatch.setattr(ApiDataServer, "LineData", BlockingLineData)

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [
            executor.submit(ApiDataServer._get_height_data_sync,
                            "S", "cache-same", 1, 2, 3, 4)
            for _ in range(8)
        ]
        assert calculation_started.wait(timeout=1)
        release_calculation.set()
        results = [future.result(timeout=2) for future in futures]

    assert results == [results[0]] * 8
    assert calls == 1


def test_height_data_cache_separates_keys_and_expires_by_ttl(monkeypatch):
    calls = 0

    class CountingLineData:
        def __init__(self, _data, _mask, point_l, point_r):
            nonlocal calls
            calls += 1
            self.point_l = point_l
            self.point_r = point_r

        def split_image_line_points(self, ray=False):
            assert ray is False
            return [[
                [self.point_l.x, self.point_l.y, calls],
                [self.point_r.x, self.point_r.y, calls],
            ]]

    monkeypatch.setattr(ApiDataServer, "DataGet", _FakeDataGet)
    monkeypatch.setattr(ApiDataServer, "LineData", CountingLineData)

    load = ApiDataServer._get_height_data_sync
    first = load("S", "cache-ttl", 1, 2, 3, 4)
    assert load("S", "cache-ttl", 1, 2, 3, 4) == first
    load("L", "cache-ttl", 1, 2, 3, 4)
    load("S", "cache-other-coil", 1, 2, 3, 4)
    load("S", "cache-ttl", 2, 2, 3, 4)
    load("S", "cache-ttl", 1, 3, 3, 4)
    load("S", "cache-ttl", 1, 2, 4, 4)
    load("S", "cache-ttl", 1, 2, 3, 5)

    assert calls == 7
    assert (ApiDataServer._height_data_cache.ttl
            == ApiDataServer._HEIGHT_DATA_CACHE_TTL_SECONDS)

    ApiDataServer._height_data_cache.expire(
        time=ApiDataServer._height_data_cache.timer()
        + ApiDataServer._height_data_cache.ttl + 1)
    assert load("S", "cache-ttl", 1, 2, 3, 4) != first
    assert calls == 8
