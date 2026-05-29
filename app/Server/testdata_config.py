from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TESTDATA_COIL_ID = "193113"
DEFAULT_SCAN3D_SCALE_X = 0.33693358302116394
DEFAULT_SCAN3D_SCALE_Y = 0.33693358302116394
DEFAULT_SCAN3D_SCALE_Z = 0.016229506582021713


def get_testdata_coil_id() -> str:
    return os.getenv("API_TESTDATA_COIL_ID", DEFAULT_TESTDATA_COIL_ID)


def get_testdata_dir() -> Path:
    explicit_dir = os.getenv("API_TESTDATA_DIR")
    if explicit_dir:
        return Path(explicit_dir)

    coil_id = get_testdata_coil_id()
    generated_dir = PROJECT_ROOT / "TestData" / "to" / coil_id
    if generated_dir.exists():
        return generated_dir

    legacy_dir = PROJECT_ROOT / "TestData" / coil_id
    if legacy_dir.exists():
        return legacy_dir

    return generated_dir


def infer_surface_key(path: Path | str) -> str | None:
    for part in Path(path).parts:
        normalized = part.replace("\\", "/").lower()
        if normalized.endswith("save_s") or normalized in {"s", "surface_s"}:
            return "S"
        if normalized.endswith("save_l") or normalized in {"l", "surface_l"}:
            return "L"
    return None


def get_testdata_asset_dir(path: Path | str | None = None) -> Path:
    base_dir = get_testdata_dir()
    if path is None:
        return base_dir

    surface_key = infer_surface_key(path)
    if surface_key is None:
        return base_dir

    surface_dir = base_dir / surface_key
    if surface_dir.exists():
        return surface_dir
    return base_dir


def _load_npz_array(path: Path) -> np.ndarray | None:
    if not path.exists():
        return None
    data = np.load(path)
    if "array" in data:
        return data["array"]
    first_key = data.files[0] if data.files else None
    return data[first_key] if first_key else None


def _surface_asset_dir(surface_key: str) -> Path:
    surface_dir = get_testdata_dir() / surface_key.upper()
    if surface_dir.exists():
        return surface_dir
    return get_testdata_dir()


def get_testdata_coil_info(surface_key: str) -> dict | None:
    surface_key = surface_key.upper()
    asset_dir = _surface_asset_dir(surface_key)
    if not asset_dir.exists():
        return None

    info = {}
    data_json = asset_dir / "data.json"
    if data_json.exists():
        try:
            info.update(json.loads(data_json.read_text(encoding="utf-8")))
        except Exception:
            info = {}

    array = _load_npz_array(asset_dir / "3D.npz")
    if array is not None:
        non_zero = array[array != 0]
        median_3d = float(np.median(non_zero)) if non_zero.size else 0.0
        height, width = array.shape[:2]
    else:
        median_3d = 0.0
        shape = info.get("shape") or [0, 0]
        height, width = int(shape[0] or 0), int(shape[1] or 0)

    info.update({
        "coilId": info.get("coilId") or get_testdata_coil_id(),
        "surface": surface_key,
        "width": int(width),
        "height": int(height),
        "scan3dCoordinateScaleX": DEFAULT_SCAN3D_SCALE_X,
        "scan3dCoordinateScaleY": DEFAULT_SCAN3D_SCALE_Y,
        "scan3dCoordinateScaleZ": DEFAULT_SCAN3D_SCALE_Z,
        "scan3dCoordinateOffsetZ": 0,
        "median_3d": median_3d,
        "median_3d_mm": median_3d * DEFAULT_SCAN3D_SCALE_Z,
        "colorFromValue_mm": -30,
        "colorToValue_mm": 30,
        "circleConfig": info.get("circleConfig") or {
            "inner_circle": {
                "circlex": [int(width / 2), int(height / 2)],
                "ellipse": []
            }
        },
    })
    return info
