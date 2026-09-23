"""Offline synthetic depth -> production Save3D -> OBJ -> Qt mesh verification.

No application config, database, camera, or PLC module is loaded. All runtime
settings are process-local stubs. The generated model is one observed surface;
no back surface, volume, or coil wall is invented.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import logging
import shutil
import sys
import time
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

import numpy as np


ROOT = Path(__file__).resolve().parents[1]


def default_balsam_path() -> Path:
    executable = shutil.which("balsam")
    if executable:
        return Path(executable)
    pyside_spec = importlib.util.find_spec("PySide6")
    if pyside_spec and pyside_spec.origin:
        candidate = Path(pyside_spec.origin).resolve().parent / "balsam.exe"
        if candidate.is_file():
            return candidate
    return Path("balsam")


def load_isolated_saver(balsam: Path, downsample: int):
    config = ModuleType("Base.CONFIG")
    config.serverConfigProperty = SimpleNamespace(balsam_exe=str(balsam))
    log = ModuleType("Base.utils.Log")
    log.logger = logging.getLogger("verify_3d_reconstruction")
    globs = ModuleType("Globs")
    globs.control = SimpleNamespace(downsampleSize=downsample, median_filter_size=1)
    spec = importlib.util.spec_from_file_location("isolated_save3d", ROOT / "app/algorithm_runtime/Save3D/save.py")
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {"Base.CONFIG": config, "Base.utils.Log": log, "Globs": globs}):
        spec.loader.exec_module(module)
    return module


def surface_height(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Known millimetre ground truth: slight slope plus two smooth deformations."""
    bulge = 8 * np.exp(-((x - 85)**2 + (y - 30)**2) / (2 * 15**2))
    recess = 5 * np.exp(-((x + 85)**2 + (y + 25)**2) / (2 * 18**2))
    return 0.012 * x + 0.008 * y + bulge - recess


def verify(output: Path, balsam: Path, downsample: int = 3) -> dict:
    output = output.resolve()
    balsam = balsam.resolve()
    if not balsam.is_file():
        raise FileNotFoundError(f"Balsam executable not found: {balsam}")
    output.mkdir(parents=True, exist_ok=True)
    saver = load_isolated_saver(balsam, downsample)
    shape = (401, 601)
    center = (300.0, 200.0)
    scales = (0.5, 0.75, 0.1)
    offset_z = 800.0
    baseline_raw = 10000.0
    baseline_mm = baseline_raw * scales[2] + offset_z
    rows, cols = np.indices(shape)
    x = (cols - center[0]) * scales[0]
    y = (rows - center[1]) * scales[1]
    radius = np.hypot(x, y)
    center_hole_radius = 60.0
    outer_radius = 130.0
    missing = ((x - 90)**2 + y**2) <= 5.0**2
    valid = (radius >= center_hole_radius) & (radius <= outer_radius) & ~missing
    depth = np.where(valid, baseline_raw + surface_height(x, y) / scales[2], 0).astype(np.float32)
    np.savez_compressed(output / "synthetic_depth.npz", array=depth, mask=valid.astype(np.uint8))
    calibration = {
        "synthetic_only": True,
        "surface_count": 1,
        "shape": list(shape),
        "center_px": list(center),
        "pixel_scale_mm": list(scales),
        "offset_z_mm": offset_z,
        "baseline_mm": baseline_mm,
        "downsample": downsample,
        "median_filter_size": 1,
        "outer_radius_mm": outer_radius,
        "center_hole_radius_mm": center_hole_radius,
        "missing_patch_center_mm": [90, 0],
        "missing_patch_radius_mm": 5,
    }
    (output / "calibration.json").write_text(json.dumps(calibration, indent=2), encoding="utf-8")
    obj_file = output / "3D.obj"
    payload = ["synthetic-annulus", depth, valid, {}, {"inner_circle": {"ellipse": [center]}},
               obj_file, baseline_mm, scales, offset_z]
    started = time.monotonic()
    if not saver._save_3d(payload, None):
        raise RuntimeError(f"mesh generation failed; see {output / 'mesh_status.json'}")
    elapsed = time.monotonic() - started
    status = json.loads((output / "mesh_status.json").read_text(encoding="utf-8"))
    mesh_files = sorted(output.rglob("*.mesh"))
    if status["optimizer_success"] is not True or not mesh_files:
        raise RuntimeError("Balsam did not produce a Qt mesh")

    loaded = saver.o3d.io.read_triangle_mesh(str(obj_file))
    vertices = np.asarray(loaded.vertices)
    triangles = np.asarray(loaded.triangles)
    if not vertices.size or not triangles.size or not np.isfinite(vertices).all():
        raise AssertionError("OBJ contains empty or invalid geometry")
    height_error = np.abs(vertices[:, 2] - surface_height(vertices[:, 0], vertices[:, 1]))
    expected, _ = saver._get_point_cloud_(payload, None)
    sample_rows = np.rint((vertices[:, 1] / scales[1] + center[1]) / downsample).astype(int)
    sample_cols = np.rint((vertices[:, 0] / scales[0] + center[0]) / downsample).astype(int)
    export_error = np.abs(vertices[:, 2] - expected["z_coords"][sample_rows, sample_cols])
    centroids = vertices[triangles].mean(axis=1)
    bridge_center = int(np.count_nonzero(np.hypot(centroids[:, 0], centroids[:, 1]) < center_hole_radius))
    bridge_patch = int(np.count_nonzero(np.hypot(centroids[:, 0] - 90, centroids[:, 1]) < 5))
    result = {
        "synthetic_only": True,
        "single_surface_only": True,
        "balsam_executable": str(balsam),
        "balsam_success": status["optimizer_success"],
        "elapsed_seconds": elapsed,
        "depth_valid_pixels": int(valid.sum()),
        "obj_file": str(obj_file),
        "obj_bytes": obj_file.stat().st_size,
        "vertices": len(vertices),
        "triangles": len(triangles),
        "bounds_min_mm": vertices.min(axis=0).tolist(),
        "bounds_max_mm": vertices.max(axis=0).tolist(),
        "dimensions_mm": np.ptp(vertices, axis=0).tolist(),
        "normal_positive_z": bool(np.all(np.asarray(loaded.vertex_normals)[:, 2] > 0)),
        "analytic_height_error_max_mm": float(height_error.max()),
        "analytic_height_error_mean_mm": float(height_error.mean()),
        "obj_export_error_max_mm": float(export_error.max()),
        "center_hole_bridge_triangles": bridge_center,
        "missing_patch_bridge_triangles": bridge_patch,
        "qt_mesh_count": len(mesh_files),
        "qt_mesh_files": [{"path": str(path), "bytes": path.stat().st_size} for path in mesh_files],
        "qt_qml_files": [str(path) for path in sorted(output.glob("*.qml"))],
        "mesh_status": status,
    }
    if bridge_center or bridge_patch:
        raise AssertionError("mesh bridges a synthetic hole")
    if height_error.max() > 0.15 or export_error.max() > 0.0001:
        raise AssertionError(f"mesh precision check failed: {result}")
    (output / "verification.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "work/3d_implementation_20260923/synthetic")
    parser.add_argument("--balsam", type=Path,
                        default=default_balsam_path())
    parser.add_argument("--downsample", type=int, default=3)
    args = parser.parse_args()
    if args.downsample < 1:
        parser.error("--downsample must be positive")
    logging.basicConfig(level=logging.INFO)
    print(json.dumps(verify(args.output, args.balsam, args.downsample), indent=2))


if __name__ == "__main__":
    main()
