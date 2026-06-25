import math
from typing import Optional

import numpy as np


def _finite_float(value) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def get_camera_z_calibration(camera_data) -> Optional[tuple[float, float]]:
    json_items = camera_data.get("json") if isinstance(camera_data, dict) else None
    if not json_items:
        return None

    try:
        coordinate_z = json_items[0]["bdConfig"]["CoordinateC"]
    except (KeyError, IndexError, TypeError):
        return None

    scale = _finite_float(coordinate_z.get("Scan3dCoordinateScale"))
    offset = _finite_float(coordinate_z.get("Scan3dCoordinateOffset"))
    if scale is None or scale <= 0 or offset is None:
        return None
    return scale, offset


def depth_to_reference_units(depth_data: np.ndarray,
                             source_scale: float,
                             source_offset: float,
                             reference_scale: float,
                             reference_offset: float) -> np.ndarray:
    source_scale = _finite_float(source_scale)
    source_offset = _finite_float(source_offset)
    reference_scale = _finite_float(reference_scale)
    reference_offset = _finite_float(reference_offset)
    if source_scale is None or source_scale <= 0 or source_offset is None:
        return depth_data
    if reference_scale is None or reference_scale <= 0:
        return depth_data
    if reference_offset is None:
        return depth_data
    if np.isclose(source_scale, reference_scale) and np.isclose(
            source_offset, reference_offset):
        return depth_data

    valid_mask = depth_data != 0
    if np.issubdtype(depth_data.dtype, np.floating):
        valid_mask &= np.isfinite(depth_data)
    if not np.any(valid_mask):
        return depth_data

    converted = np.zeros_like(depth_data)
    values = (
        depth_data[valid_mask].astype(np.float32) * source_scale +
        source_offset - reference_offset
    ) / reference_scale

    if np.issubdtype(depth_data.dtype, np.integer):
        dtype_info = np.iinfo(depth_data.dtype)
        values = np.clip(np.rint(values), dtype_info.min, dtype_info.max)
        converted[valid_mask] = values.astype(depth_data.dtype)
    else:
        converted[valid_mask] = values.astype(depth_data.dtype, copy=False)
    return converted


def align_camera_depth_planes(datas,
                              reference_scale: float,
                              reference_offset: float) -> list[dict]:
    reference_scale = _finite_float(reference_scale)
    reference_offset = _finite_float(reference_offset)
    if reference_scale is None or reference_scale <= 0 or reference_offset is None:
        return []

    adjustments = []
    for index, data in enumerate(datas):
        depth_data = data.get("3D") if isinstance(data, dict) else None
        if depth_data is None:
            continue

        calibration = get_camera_z_calibration(data)
        if calibration is None:
            continue
        source_scale, source_offset = calibration
        aligned_depth = depth_to_reference_units(depth_data, source_scale,
                                                source_offset,
                                                reference_scale,
                                                reference_offset)
        if aligned_depth is depth_data:
            continue

        data["3D"] = aligned_depth
        adjustments.append({
            "index": index,
            "camera": str(data.get("camera", "")),
            "sourceScaleZ": float(source_scale),
            "sourceOffsetZ": float(source_offset),
            "referenceScaleZ": float(reference_scale),
            "referenceOffsetZ": float(reference_offset),
            "rawOffsetToReference": float(
                (source_offset - reference_offset) / reference_scale),
        })
    return adjustments
