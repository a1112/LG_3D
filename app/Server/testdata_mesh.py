from __future__ import annotations

import math
from pathlib import Path

import numpy as np

from testdata_config import DEFAULT_SCAN3D_SCALE_X, DEFAULT_SCAN3D_SCALE_Y, DEFAULT_SCAN3D_SCALE_Z, get_testdata_dir


DEFAULT_OBJ_NAME = "defaultobject.obj"


def _load_npz_array(npz_path: Path) -> np.ndarray:
    with np.load(npz_path) as data:
        if "array" in data:
            return data["array"]
        if not data.files:
            raise ValueError(f"empty npz file: {npz_path}")
        return data[data.files[0]]


def _sample_heightmap(data: np.ndarray, max_size: int) -> tuple[np.ndarray, int]:
    if data.ndim > 2:
        data = data[:, :, 0]
    height, width = data.shape[:2]
    step = max(1, int(math.ceil(max(height, width) / max_size)))
    return data[::step, ::step], step


def write_heightmap_obj(npz_path: Path | str, obj_path: Path | str, max_size: int = 320) -> Path:
    """
    Convert compressed 3D height data into a lightweight OBJ surface for QtQuick3D RuntimeLoader.

    The OBJ is a sampled single-surface mesh. Zero-height cells are treated as holes so the coil center remains open.
    """
    npz_path = Path(npz_path)
    obj_path = Path(obj_path)
    data = _load_npz_array(npz_path).astype(np.float32, copy=False)
    sampled, step = _sample_heightmap(data, max_size=max_size)
    valid = np.isfinite(sampled) & (sampled > 0)
    if int(np.count_nonzero(valid)) < 3:
        raise ValueError(f"not enough valid 3D points to build mesh: {npz_path}")

    rows, cols = sampled.shape[:2]
    valid_values = sampled[valid]
    median_z = float(np.median(valid_values)) if valid_values.size else 0.0
    index_map = np.full((rows, cols), -1, dtype=np.int32)

    obj_path.parent.mkdir(parents=True, exist_ok=True)
    with obj_path.open("w", encoding="ascii", newline="\n") as file:
        file.write("# Generated from LG_3D compressed 3D.npz\n")
        vertex_index = 1
        center_row = (rows - 1) / 2.0
        center_col = (cols - 1) / 2.0
        for row in range(rows):
            for col in range(cols):
                if not valid[row, col]:
                    continue
                x = (col - center_col) * step * DEFAULT_SCAN3D_SCALE_X
                y = (row - center_row) * step * DEFAULT_SCAN3D_SCALE_Y
                z = (float(sampled[row, col]) - median_z) * DEFAULT_SCAN3D_SCALE_Z
                file.write(f"v {x:.6f} {y:.6f} {z:.6f}\n")
                index_map[row, col] = vertex_index
                vertex_index += 1

        face_count = 0
        for row in range(rows - 1):
            for col in range(cols - 1):
                p00 = index_map[row, col]
                p01 = index_map[row, col + 1]
                p10 = index_map[row + 1, col]
                p11 = index_map[row + 1, col + 1]
                if p00 > 0 and p10 > 0 and p01 > 0:
                    file.write(f"f {p00} {p10} {p01}\n")
                    face_count += 1
                if p10 > 0 and p11 > 0 and p01 > 0:
                    file.write(f"f {p10} {p11} {p01}\n")
                    face_count += 1

    if face_count == 0:
        obj_path.unlink(missing_ok=True)
        raise ValueError(f"not enough connected valid 3D cells to build mesh: {npz_path}")
    return obj_path


def ensure_testdata_mesh(surface_key: str, coil_id: str | int | None = None, max_size: int = 320) -> Path:
    surface = str(surface_key or "").upper()
    if surface not in {"S", "L"}:
        raise ValueError(f"invalid surface key: {surface_key}")

    base_dir = get_testdata_dir()
    surface_dir = base_dir / surface
    if not surface_dir.exists():
        surface_dir = base_dir

    obj_path = surface_dir / "meshes" / DEFAULT_OBJ_NAME
    npz_path = surface_dir / "3D.npz"
    if not npz_path.exists():
        raise FileNotFoundError(str(npz_path))

    if obj_path.exists() and obj_path.stat().st_mtime >= npz_path.stat().st_mtime:
        return obj_path
    return write_heightmap_obj(npz_path, obj_path, max_size=max_size)
