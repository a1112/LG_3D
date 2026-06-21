import asyncio
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SERVER_ROOT = PROJECT_ROOT / "app" / "Server"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))
if str(PROJECT_ROOT / "app") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "app"))

from app.Server.api import ApiDataServer


class FakeDataGet:
    def __init__(self, *_args, **_kwargs):
        self.mask = np.zeros((11, 401), dtype=np.uint8)
        self.mask[5, 5:10] = 255
        self.mask[5, 20:140] = 255
        self.mask[5, 260:380] = 255
        self.mask[5, 390:395] = 255
        self.data = np.arange(11 * 401, dtype=np.int32).reshape(11, 401)

    def get_image(self, pil=False):
        if pil:
            return Image.fromarray(self.mask)
        return self.mask

    def get_3d_data(self):
        return self.data


def test_height_data_returns_full_cross_line_segments(monkeypatch):
    monkeypatch.setattr(ApiDataServer, "DataGet", FakeDataGet)

    result = asyncio.run(ApiDataServer.get_height_data("S", "193113", x1=200, y1=5, x2=400, y2=5))

    assert len(result) == 2
    assert result[0]["pointL"] == [20, 5]
    assert result[0]["pointR"] == [139, 5]
    assert result[1]["pointL"] == [260, 5]
    assert result[1]["pointR"] == [379, 5]


def test_error_cache_match_preserves_float_thresholds(tmp_path):
    error_path = tmp_path / "Error.png"
    error_path.write_bytes(b"")
    error_path.with_suffix(".json").write_text(json.dumps({
        "threshold_down": 50.5,
        "threshold_up": 80.25,
    }), encoding="utf-8")

    assert ApiDataServer._error_cache_matches(error_path, 50.5, 80.25)
    assert ApiDataServer._error_cache_matches(error_path, -50.5, -80.25)
    assert not ApiDataServer._error_cache_matches(error_path, 50.0, 80.25)
    assert not ApiDataServer._error_cache_matches(error_path, 50.5, 80.0)


def test_error_render_baseline_ignores_invalid_coil_state(monkeypatch):
    monkeypatch.setattr(
        ApiDataServer,
        "get_coil_state_by_coil_id",
        lambda *_args: type("BadState", (), {
            "scan3dCoordinateScaleZ": float("nan"),
            "median_3d": float("nan"),
        })(),
    )
    npy_data = np.array([
        [0, 1000, 2000],
        [3000, 4000, 0],
    ], dtype=np.int32)

    median_z_int, scale_factor = ApiDataServer._get_error_render_baseline("1001", "S", npy_data)

    assert median_z_int == 3000
    assert scale_factor == ApiDataServer.DEFAULT_ERROR_SCALE_FACTOR


def test_error_render_baseline_prefers_valid_coil_state(monkeypatch):
    monkeypatch.setattr(
        ApiDataServer,
        "get_coil_state_by_coil_id",
        lambda *_args: type("GoodState", (), {
            "scan3dCoordinateScaleZ": 0.02,
            "median_3d": 2500,
        })(),
    )
    npy_data = np.array([[2000, 3000, 4000]], dtype=np.int32)

    median_z_int, scale_factor = ApiDataServer._get_error_render_baseline("1001", "S", npy_data)

    assert median_z_int == 2500
    assert scale_factor == 0.02
