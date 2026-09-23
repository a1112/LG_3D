from __future__ import annotations

import math
import json
import os
import tempfile
from pathlib import Path

import numpy as np

from testdata_config import (DEFAULT_SCAN3D_SCALE_X, DEFAULT_SCAN3D_SCALE_Y,
                             DEFAULT_SCAN3D_SCALE_Z, get_testdata_dir)

DEFAULT_OBJ_NAME = "defaultobject.obj"


def _load_heightmap_array(data_path: Path) -> np.ndarray:
    """Load either the compressed NPZ or plain NPY test-data format."""
    loaded = np.load(data_path, allow_pickle=False)
    if isinstance(loaded, np.ndarray):
        return loaded
    with loaded:
        if "array" in loaded:
            return np.array(loaded["array"], copy=True)
        if not loaded.files:
            raise ValueError(f"empty npz file: {data_path}")
        return np.array(loaded[loaded.files[0]], copy=True)


def _mesh_scales(data_path: Path) -> tuple[float, float, float]:
    scales = (DEFAULT_SCAN3D_SCALE_X, DEFAULT_SCAN3D_SCALE_Y,
              DEFAULT_SCAN3D_SCALE_Z)
    metadata_path = data_path.parent / "data.json"
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError, TypeError):
        return scales
    values = []
    if not isinstance(metadata, dict):
        return scales
    for key, fallback in zip(
        ("scan3dCoordinateScaleX", "scan3dCoordinateScaleY",
         "scan3dCoordinateScaleZ"), scales):
        try:
            value = float(metadata.get(key, fallback))
            values.append(
                value if math.isfinite(value) and value > 0 else fallback)
        except (TypeError, ValueError):
            values.append(fallback)
    return tuple(values)


def _sample_heightmap(data: np.ndarray,
                      max_size: int) -> tuple[np.ndarray, np.ndarray, int]:
    if data.ndim > 2:
        data = data[:, :, 0]
    height, width = data.shape[:2]
    step = max(1, int(math.ceil(max(height, width) / max_size)))
    sampled = data[::step, ::step]
    sampled_valid = np.zeros(sampled.shape, dtype=bool)
    source_valid = np.isfinite(data) & (data > 0)
    for row, source_row in enumerate(range(0, height, step)):
        for col, source_col in enumerate(range(0, width, step)):
            sampled_valid[row, col] = np.all(
                source_valid[source_row:min(source_row + step, height),
                             source_col:min(source_col + step, width)])
    return sampled, sampled_valid, step


def write_heightmap_obj(npz_path: Path | str,
                        obj_path: Path | str,
                        max_size: int = 320) -> Path:
    """
    Convert compressed 3D height data into a lightweight OBJ surface for QtQuick3D RuntimeLoader.

    The OBJ is a sampled single-surface mesh. Zero-height cells are treated as holes so the coil center remains open.
    """
    npz_path = Path(npz_path)
    obj_path = Path(obj_path)
    if max_size <= 0:
        raise ValueError("max_size must be greater than zero")
    data = _load_heightmap_array(npz_path).astype(np.float32, copy=False)
    if data.ndim == 3:
        data = data[:, :, 0]
    if data.ndim != 2:
        raise ValueError(f"3D data must be a 2D heightmap: {npz_path}")
    if data.shape[0] == 0 or data.shape[1] == 0:
        raise ValueError(f"3D data must not be empty: {npz_path}")
    sampled, sampled_valid, step = _sample_heightmap(data, max_size=max_size)
    scale_x, scale_y, scale_z = _mesh_scales(npz_path)
    valid = sampled_valid
    if int(np.count_nonzero(valid)) < 3:
        raise ValueError(
            f"not enough valid 3D points to build mesh: {npz_path}")

    rows, cols = sampled.shape[:2]
    valid_values = sampled[valid]
    median_z = float(np.median(valid_values)) if valid_values.size else 0.0
    index_map = np.full((rows, cols), -1, dtype=np.int32)

    obj_path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{obj_path.name}.",
                                     suffix=".tmp",
                                     dir=obj_path.parent)
    os.close(fd)
    temp_path = Path(temp_name)
    try:
        with temp_path.open("w", encoding="ascii", newline="\n") as file:
            file.write(
                f"# Generated from LG_3D heightmap max_size={max_size}\n")
            vertex_index = 1
            center_row = (rows - 1) / 2.0
            center_col = (cols - 1) / 2.0
            for row in range(rows):
                for col in range(cols):
                    if not valid[row, col]:
                        continue
                    x = (col - center_col) * step * scale_x
                    y = (row - center_row) * step * scale_y
                    z = (float(sampled[row, col]) - median_z) * scale_z
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
            raise ValueError(
                f"not enough connected valid 3D cells to build mesh: {npz_path}"
            )
        os.replace(temp_path, obj_path)
        return obj_path
    finally:
        temp_path.unlink(missing_ok=True)


def ensure_testdata_mesh(surface_key: str,
                         coil_id: str | int | None = None,
                         max_size: int = 320) -> Path:
    surface = str(surface_key or "").upper()
    if surface not in {"S", "L"}:
        raise ValueError(f"invalid surface key: {surface_key}")

    base_dir = get_testdata_dir()
    surface_dir = base_dir / surface
    if not surface_dir.exists():
        surface_dir = base_dir

    obj_path = surface_dir / "meshes" / DEFAULT_OBJ_NAME
    data_path = next(
        (surface_dir / name
         for name in ("3D.npz", "3D.npy") if (surface_dir / name).exists()),
        None)
    if data_path is None:
        raise FileNotFoundError(str(surface_dir / "3D.npz"))

    metadata_path = data_path.parent / "data.json"
    newest_source = max(
        data_path.stat().st_mtime_ns,
        metadata_path.stat().st_mtime_ns if metadata_path.exists() else 0)
    if obj_path.exists() and obj_path.stat().st_mtime_ns >= newest_source:
        try:
            header = obj_path.open(encoding="ascii").readline()
            if f"max_size={max_size}" in header:
                return obj_path
        except (OSError, UnicodeDecodeError):
            pass
    return write_heightmap_obj(data_path, obj_path, max_size=max_size)
