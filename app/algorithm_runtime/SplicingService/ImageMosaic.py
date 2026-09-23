import asyncio
import json
import os
import threading
import time
from pathlib import Path
from queue import Empty, Full
from typing import List, Optional

import cv2
import numpy as np
from PIL import Image

# import AlarmDetection
from Save3D.save import D3Saver

from Base.property.ErrorBase import ServerDetectionException
from Base.tools.compressed_storage import atomic_write_bytes
from utils.DetectionSpeedRecord import DetectionSpeedRecord
from Base.tools import tool  # FlattenSurface

from Base.CONFIG import isLoc, serverConfigProperty
from Init import ColorMaps, PreviewSize
from .DataFolder import DataFolder
from .ImageSaver import ImageSaver
from .capture_paths import align_capture_frame_sequences
from .depth_plane import align_camera_depth_planes
from .taper_error_threshold import taper_error_threshold_from_limits
from algorithm_runtime.runtime_heartbeat import runtime_heartbeat
from Globs import control
from Base.property.Base import DataIntegration

from Base.utils.Log import logger
from Base.utils.LoggerProcess import LoggerProcess

import Globs

DEFAULT_MOSAIC_QUEUE_PUT_TIMEOUT = 2.0
DEFAULT_MOSAIC_RESULT_TIMEOUT = 60.0
DEFAULT_DEPTH_GAP_FILL_ITERATIONS = 16


def _get_mosaic_queue_put_timeout() -> float:
    raw_value = os.getenv("LG3D_MOSAIC_QUEUE_PUT_TIMEOUT",
                          str(DEFAULT_MOSAIC_QUEUE_PUT_TIMEOUT))
    try:
        return max(float(raw_value), 0.1)
    except ValueError:
        logger.warning("invalid LG3D_MOSAIC_QUEUE_PUT_TIMEOUT=%s, use %s",
                       raw_value, DEFAULT_MOSAIC_QUEUE_PUT_TIMEOUT)
        return DEFAULT_MOSAIC_QUEUE_PUT_TIMEOUT


def _get_mosaic_result_timeout() -> float:
    raw_value = os.getenv("LG3D_MOSAIC_RESULT_TIMEOUT",
                          str(DEFAULT_MOSAIC_RESULT_TIMEOUT))
    try:
        return max(float(raw_value), 0.1)
    except ValueError:
        logger.warning("invalid LG3D_MOSAIC_RESULT_TIMEOUT=%s, use %s",
                       raw_value, DEFAULT_MOSAIC_RESULT_TIMEOUT)
        return DEFAULT_MOSAIC_RESULT_TIMEOUT


def _get_depth_gap_fill_iterations() -> int:
    raw_value = os.getenv("LG3D_DEPTH_GAP_FILL_ITERATIONS",
                          str(DEFAULT_DEPTH_GAP_FILL_ITERATIONS))
    try:
        return max(int(raw_value), 0)
    except ValueError:
        logger.warning(
            "invalid LG3D_DEPTH_GAP_FILL_ITERATIONS=%s, use %s",
            raw_value,
            DEFAULT_DEPTH_GAP_FILL_ITERATIONS,
        )
        return DEFAULT_DEPTH_GAP_FILL_ITERATIONS


def leveling_2d(datas):
    if Globs.control.leveling_gray:  # 调整灰度
        media_gray_list = []
        for data in datas:
            image_2d = data.get("2D")
            if image_2d is None or image_2d.size == 0:
                logger.warning("leveling_2d skip empty image: camera=%s",
                               data.get("camera"))
                return
            valid_gray = image_2d[image_2d != 0]
            if valid_gray.size == 0:
                logger.warning("leveling_2d skip all-zero image: camera=%s",
                               data.get("camera"))
                return
            media_gray = float(np.median(valid_gray))
            media_gray_list.append(media_gray)
        logger.debug("leveling_2d medians=%s", media_gray_list)
        if len(media_gray_list) < 3 or media_gray_list[1] <= 0:
            logger.warning("leveling_2d skip invalid medians: %s",
                           media_gray_list)
            return
        ratio_list = [gray / media_gray_list[1] for gray in media_gray_list]
        if min(ratio_list) < 0.4 or max(ratio_list) > 2.5:
            logger.error("leveling_2d failed: medians=%s, ratios=%s",
                         media_gray_list, ratio_list)
            return
        for index in (0, 2):
            if media_gray_list[index] <= 0:
                continue
            scale = media_gray_list[1] / media_gray_list[index]
            datas[index]["2D"] = np.clip(
                datas[index]["2D"].astype(np.float32) * scale, 0,
                255).astype(np.uint8)


def _camera_overlap_width(cross_point, direction, left_width, right_width):
    if not cross_point or len(cross_point) < 2:
        return 0
    overlap = cross_point[0] if direction == "L" else cross_point[1]
    overlap = max(int(overlap), 0)
    if overlap > serverConfigProperty.max_clip_mun:
        return 0
    return min(overlap, int(left_width), int(right_width))


def _feather_camera_pair(left_image, left_mask, left_validity, right_image,
                         right_mask, right_validity, overlap):
    if overlap <= 0:
        return (
            np.hstack((left_image, right_image)),
            np.hstack((left_mask, right_mask)),
            np.hstack((left_validity, right_validity)),
        )

    left_overlap = left_image[:, -overlap:]
    right_overlap = right_image[:, :overlap]
    left_active = ((left_mask[:, -overlap:] > 150)
                   & (left_validity[:, -overlap:] > 0))
    right_active = ((right_mask[:, :overlap] > 150)
                    & (right_validity[:, :overlap] > 0))
    both_active = left_active & right_active

    weights = np.linspace(0.0, 1.0, overlap, dtype=np.float32)[None, :]
    blended = np.zeros_like(left_overlap)
    weighted = (left_overlap.astype(np.float32) * (1.0 - weights) +
                right_overlap.astype(np.float32) * weights)
    blended[both_active] = np.clip(np.rint(weighted[both_active]), 0,
                                   255).astype(np.uint8)
    blended[left_active & ~right_active] = left_overlap[left_active
                                                        & ~right_active]
    blended[right_active & ~left_active] = right_overlap[right_active
                                                         & ~left_active]

    overlap_mask = np.maximum(left_mask[:, -overlap:], right_mask[:, :overlap])
    overlap_validity = np.maximum(left_validity[:, -overlap:],
                                  right_validity[:, :overlap])
    return (
        np.hstack((left_image[:, :-overlap], blended, right_image[:,
                                                                  overlap:])),
        np.hstack(
            (left_mask[:, :-overlap], overlap_mask, right_mask[:, overlap:])),
        np.hstack((left_validity[:, :-overlap], overlap_validity,
                   right_validity[:, overlap:])),
    )


def feather_camera_images(datas, cross_points, direction):
    if not datas:
        raise ValueError("no camera images to feather")
    join_image = datas[0]["2D"]
    join_mask = datas[0]["MASK"]
    join_validity = datas[0]["VALIDITY"]
    for index, data in enumerate(datas[1:]):
        cross_point = cross_points[index] if index < len(cross_points) else (0,
                                                                             0)
        overlap = _camera_overlap_width(cross_point, direction,
                                        join_image.shape[1],
                                        data["2D"].shape[1])
        join_image, join_mask, join_validity = _feather_camera_pair(
            join_image,
            join_mask,
            join_validity,
            data["2D"],
            data["MASK"],
            data["VALIDITY"],
            overlap,
        )
    return join_image, join_mask, join_validity


def prepare_camera_depths_for_join(datas, cross_points, direction):
    """Trim depth overlaps while falling back to the camera with valid data."""
    for index in range(1, len(datas)):
        left = datas[index - 1]
        right = datas[index]
        overlap = _camera_overlap_width(
            cross_points[index - 1],
            direction,
            left["3D"].shape[1],
            right["3D"].shape[1],
        )
        if overlap <= 0:
            continue

        left_depth = left["3D"]
        right_depth = right["3D"]
        left_overlap = left_depth[:, -overlap:]
        right_overlap = right_depth[:, :overlap]
        left_active = ((left["VALIDITY"][:, -overlap:] > 0)
                       & (left["MASK"][:, -overlap:] > 150)
                       & (left_overlap > 0))
        right_active = ((right["VALIDITY"][:, :overlap] > 0)
                        & (right["MASK"][:, :overlap] > 150)
                        & (right_overlap > 0))

        if direction == "L":
            merged = np.zeros_like(right_overlap)
            merged[right_active] = right_overlap[right_active]
            fallback = ~right_active & left_active
            merged[fallback] = left_overlap[fallback]
            right_depth = right_depth.copy()
            right_depth[:, :overlap] = merged
            left["3D"] = left_depth[:, :-overlap]
            right["3D"] = right_depth
        else:
            merged = np.zeros_like(left_overlap)
            merged[left_active] = left_overlap[left_active]
            fallback = ~left_active & right_active
            merged[fallback] = right_overlap[fallback]
            left_depth = left_depth.copy()
            left_depth[:, -overlap:] = merged
            left["3D"] = left_depth
            right["3D"] = right_depth[:, overlap:]
    return [data["3D"] for data in datas]


def _boundary_band_slices(left_width, right_width, cross_point, direction,
                          band_width):
    overlap = _camera_overlap_width(cross_point, direction, left_width,
                                    right_width)
    left_end = left_width - overlap if direction == "L" else left_width
    right_start = 0 if direction == "L" else overlap
    width = min(int(band_width), int(left_end), int(right_width - right_start))
    if width <= 0:
        return None
    return slice(left_end - width, left_end), slice(right_start,
                                                    right_start + width)


def _masked_row_median(image, active_mask, column_slice):
    band = image[:, column_slice]
    active = active_mask[:, column_slice]
    values = np.ma.array(band, mask=~active)
    medians = np.ma.median(values, axis=1).filled(np.nan).astype(np.float32)
    minimum_points = max(4, int(band.shape[1] * 0.15))
    medians[np.count_nonzero(active, axis=1) < minimum_points] = np.nan
    return medians


def _smooth_row_correction(correction, max_abs=80.0, window_size=101):
    valid_rows = np.flatnonzero(np.isfinite(correction))
    if valid_rows.size < 2:
        return None
    rows = np.arange(correction.size)
    filled = np.interp(rows, valid_rows, correction[valid_rows])
    window_size = min(int(window_size), correction.size)
    if window_size % 2 == 0:
        window_size -= 1
    if window_size >= 3:
        padding = window_size // 2
        padded = np.pad(filled, (padding, padding), mode="edge")
        kernel = np.full(window_size, 1.0 / window_size, dtype=np.float32)
        filled = np.convolve(padded, kernel, mode="valid")
    return np.clip(filled, -float(max_abs), float(max_abs)).astype(np.float32)


def _apply_row_correction(data, correction):
    image = data["2D"]
    active = ((data["MASK"] > 150) & (data["VALIDITY"] > 0) & (image > 0))
    adjusted = image.astype(np.float32)
    adjusted += correction[:, None] * active
    data["2D"] = np.clip(np.rint(adjusted), 0, 255).astype(np.uint8)
    data["gray_boundary_correction"] = {
        "min": float(np.min(correction)),
        "median": float(np.median(correction)),
        "max": float(np.max(correction)),
    }


def level_camera_boundaries(datas, cross_points, direction, band_width=64):
    if not Globs.control.leveling_gray or len(datas) < 2:
        return
    reference_index = len(datas) // 2

    for index in range(reference_index - 1, -1, -1):
        left = datas[index]
        right = datas[index + 1]
        slices = _boundary_band_slices(left["2D"].shape[1],
                                       right["2D"].shape[1],
                                       cross_points[index], direction,
                                       band_width)
        if slices is None:
            continue
        left_slice, right_slice = slices
        left_active = (left["MASK"] > 150) & (left["VALIDITY"] > 0)
        right_active = (right["MASK"] > 150) & (right["VALIDITY"] > 0)
        correction = (
            _masked_row_median(right["2D"], right_active, right_slice) -
            _masked_row_median(left["2D"], left_active, left_slice))
        correction = _smooth_row_correction(correction)
        if correction is not None:
            _apply_row_correction(left, correction)

    for index in range(reference_index, len(datas) - 1):
        left = datas[index]
        right = datas[index + 1]
        slices = _boundary_band_slices(left["2D"].shape[1],
                                       right["2D"].shape[1],
                                       cross_points[index], direction,
                                       band_width)
        if slices is None:
            continue
        left_slice, right_slice = slices
        left_active = (left["MASK"] > 150) & (left["VALIDITY"] > 0)
        right_active = (right["MASK"] > 150) & (right["VALIDITY"] > 0)
        correction = (
            _masked_row_median(left["2D"], left_active, left_slice) -
            _masked_row_median(right["2D"], right_active, right_slice))
        correction = _smooth_row_correction(correction)
        if correction is not None:
            _apply_row_correction(right, correction)


def _draw_filled_ellipse_or_contour(shape, contour):
    image = np.zeros(shape, dtype=np.uint8)
    if contour is None:
        return image
    if len(contour) >= 5:
        cv2.ellipse(image, cv2.fitEllipse(contour), 255, thickness=cv2.FILLED)
    else:
        cv2.drawContours(image, [contour], -1, 255, thickness=cv2.FILLED)
    return image


def _fit_contour_ellipse(contour):
    if contour is None or len(contour) < 5:
        return None
    return cv2.fitEllipse(contour)


def _is_plausible_inner_ellipse(inner_ellipse, outer_ellipse):
    if inner_ellipse is None or outer_ellipse is None:
        return False

    (inner_x, inner_y), inner_axes, _ = inner_ellipse
    (outer_x, outer_y), outer_axes, _ = outer_ellipse
    inner_min, inner_max = sorted(inner_axes)
    outer_min, outer_max = sorted(outer_axes)
    if outer_min <= 0 or inner_min <= 0:
        return False

    center_distance = np.hypot(inner_x - outer_x, inner_y - outer_y)
    return (
        center_distance <= outer_min * 0.12
        and inner_min >= outer_min * 0.12
        and inner_max <= outer_max * 0.72
        and inner_max / inner_min <= 1.35
    )


def _estimate_inner_ellipse_from_radial_edges(binary, outer_ellipse):
    """Recover the inner ellipse from intact arcs when its hole reaches outside."""
    if outer_ellipse is None:
        return None

    (center_x, center_y), outer_axes, _ = outer_ellipse
    outer_radius = min(outer_axes) / 2.0
    max_radius = int(outer_radius * 0.72)
    min_radius = int(outer_radius * 0.12)
    if max_radius <= min_radius:
        return None

    height, width = binary.shape
    points = []
    radial_distances = []
    for angle in np.linspace(0, 2 * np.pi, 360, endpoint=False):
        cos_angle = np.cos(angle)
        sin_angle = np.sin(angle)
        radii = np.arange(min_radius, max_radius + 1)
        xs = np.rint(center_x + radii * cos_angle).astype(np.int32)
        ys = np.rint(center_y + radii * sin_angle).astype(np.int32)
        inside = (xs >= 0) & (xs < width) & (ys >= 0) & (ys < height)
        xs = xs[inside]
        ys = ys[inside]
        radii = radii[inside]
        if radii.size < 3:
            continue

        foreground = binary[ys, xs] > 0
        stable_foreground = np.convolve(
            foreground.astype(np.uint8), np.ones(3, dtype=np.uint8),
            mode="valid") == 3
        stable_foreground &= np.r_[False, ~foreground[:-3]]
        transitions = np.flatnonzero(stable_foreground)
        if transitions.size == 0:
            continue
        index = int(transitions[0])
        radius = int(radii[index])
        points.append((float(xs[index]), float(ys[index])))
        radial_distances.append(radius)

    if len(points) < 120:
        return None

    radial_distances = np.asarray(radial_distances, dtype=np.float32)
    median_radius = float(np.median(radial_distances))
    keep = ((radial_distances >= median_radius * 0.7)
            & (radial_distances <= median_radius * 1.3))
    filtered_points = np.asarray(points, dtype=np.float32)[keep]
    if len(filtered_points) < 100:
        return None

    contour = np.rint(filtered_points).astype(np.int32).reshape(-1, 1, 2)
    ellipse = cv2.fitEllipse(contour)
    if not _is_plausible_inner_ellipse(ellipse, outer_ellipse):
        return None
    return ellipse


def _clean_annulus_mask(mask):
    source = np.asarray(mask)
    if source.ndim != 2 or source.size == 0:
        return mask

    binary = np.where(source > 150, 255, 0).astype(np.uint8)
    if not np.any(binary):
        return mask

    height, width = binary.shape
    close_height = max(7, min(31, height // 180))
    if close_height % 2 == 0:
        close_height += 1
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, close_height))
    closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=1)

    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL,
                                   cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return mask

    outer_contour = max(contours, key=cv2.contourArea)
    if cv2.contourArea(outer_contour) < binary.size * 0.1:
        return mask

    outer_mask = _draw_filled_ellipse_or_contour(binary.shape, outer_contour)
    hole_candidates = np.where((outer_mask > 0) & (closed == 0), 255,
                               0).astype(np.uint8)
    component_count, labels, stats, centroids = cv2.connectedComponentsWithStats(
        hole_candidates, 8)
    image_center = np.array([width / 2, height / 2], dtype=np.float32)
    best_index = None
    best_score = None
    min_hole_area = binary.size * 0.005

    for index in range(1, component_count):
        area = stats[index, cv2.CC_STAT_AREA]
        if area < min_hole_area:
            continue
        centroid = np.array(centroids[index], dtype=np.float32)
        distance = np.linalg.norm(centroid - image_center)
        score = distance / max(area**0.5, 1.0)
        if best_score is None or score < best_score:
            best_index = index
            best_score = score

    if best_index is None:
        return outer_mask.astype(source.dtype, copy=False)

    hole_component = np.where(labels == best_index, 255, 0).astype(np.uint8)
    hole_contours, _ = cv2.findContours(hole_component, cv2.RETR_EXTERNAL,
                                        cv2.CHAIN_APPROX_SIMPLE)
    if not hole_contours:
        return outer_mask.astype(source.dtype, copy=False)

    hole_contour = max(hole_contours, key=cv2.contourArea)
    outer_ellipse = _fit_contour_ellipse(outer_contour)
    hole_ellipse = _fit_contour_ellipse(hole_contour)
    if not _is_plausible_inner_ellipse(hole_ellipse, outer_ellipse):
        recovered_ellipse = _estimate_inner_ellipse_from_radial_edges(
            closed, outer_ellipse)
        if recovered_ellipse is not None:
            logger.warning(
                "recovered inner coil ellipse from intact arcs: rejected=%s recovered=%s",
                hole_ellipse,
                recovered_ellipse,
            )
            hole_ellipse = recovered_ellipse

    hole_mask = np.zeros(binary.shape, dtype=np.uint8)
    if _is_plausible_inner_ellipse(hole_ellipse, outer_ellipse):
        cv2.ellipse(hole_mask, hole_ellipse, 255, thickness=cv2.FILLED)
    else:
        logger.warning(
            "skip implausible inner coil hole: inner=%s outer=%s",
            hole_ellipse,
            outer_ellipse,
        )
    clean_mask = outer_mask.copy()
    clean_mask[hole_mask > 0] = 0
    return clean_mask.astype(source.dtype, copy=False)


def _fill_masked_zero_gaps(npy_data, mask, iterations=None):
    if npy_data.shape[:2] != mask.shape[:2] or npy_data.size == 0:
        return npy_data

    if iterations is None:
        iterations = _get_depth_gap_fill_iterations()
    if iterations <= 0:
        return npy_data

    def fill_bounded_zero_runs(data, foreground_mask, max_gap):
        changed = False
        for col in range(data.shape[1]):
            line = data[:, col]
            holes = np.flatnonzero(foreground_mask[:, col] & (line == 0))
            if holes.size == 0:
                continue

            start = int(holes[0])
            previous = start
            for hole in holes[1:]:
                hole = int(hole)
                if hole == previous + 1:
                    previous = hole
                    continue
                changed = fill_run(line, start, previous, max_gap) or changed
                start = previous = hole
            changed = fill_run(line, start, previous, max_gap) or changed
        return changed

    def fill_run(line, start, end, max_gap):
        length = end - start + 1
        if length > max_gap:
            return False
        before = start - 1
        after = end + 1
        if before < 0 or after >= line.shape[0]:
            return False
        before_value = line[before]
        after_value = line[after]
        if before_value <= 0 or after_value <= 0:
            return False
        values = np.linspace(float(before_value), float(after_value),
                             length + 2)[1:-1]
        line[start:end + 1] = values
        return True

    filled = npy_data.copy()
    foreground = mask > 0
    for _ in range(iterations):
        changed = False
        if filled.shape[0] > 2:
            up = filled[:-2, :]
            center = filled[1:-1, :]
            down = filled[2:, :]
            fill_rows = foreground[1:-1, :] & (center == 0) & (up > 0) & (down
                                                                          > 0)
            if np.any(fill_rows):
                center[fill_rows] = ((up[fill_rows].astype(np.uint32) +
                                      down[fill_rows].astype(np.uint32)) // 2)
                changed = True
        if filled.shape[1] > 2:
            left = filled[:, :-2]
            center = filled[:, 1:-1]
            right = filled[:, 2:]
            fill_cols = foreground[:, 1:-1] & (center
                                               == 0) & (left > 0) & (right > 0)
            if np.any(fill_cols):
                center[fill_cols] = ((left[fill_cols].astype(np.uint32) +
                                      right[fill_cols].astype(np.uint32)) // 2)
                changed = True
        if not changed:
            break
    fill_bounded_zero_runs(filled, foreground, iterations)
    fill_bounded_zero_runs(filled.T, foreground.T, iterations)
    return filled.astype(npy_data.dtype, copy=False)


def _fill_masked_gray_gaps(image, mask, max_gap=None, dark_threshold=15):
    if image.shape[:2] != mask.shape[:2] or image.size == 0:
        return image

    if max_gap is None:
        max_gap = _get_depth_gap_fill_iterations()
    if max_gap <= 0:
        return image

    def fill_line(line, hole_line, limit):
        changed = False
        holes = np.flatnonzero(hole_line)
        if holes.size == 0:
            return changed

        start = int(holes[0])
        previous = start
        for hole in holes[1:]:
            hole = int(hole)
            if hole == previous + 1:
                previous = hole
                continue
            changed = fill_run(line, start, previous, limit) or changed
            start = previous = hole
        return fill_run(line, start, previous, limit) or changed

    def fill_run(line, start, end, limit):
        length = end - start + 1
        if length > limit:
            return False
        before = start - 1
        after = end + 1
        if before < 0 or after >= line.shape[0]:
            return False
        before_value = line[before]
        after_value = line[after]
        if before_value <= dark_threshold or after_value <= dark_threshold:
            return False
        values = np.linspace(float(before_value), float(after_value),
                             length + 2)[1:-1]
        line[start:end + 1] = values
        return True

    filled = image.copy()
    if filled.ndim == 2:
        channels = [filled]
        gray = filled
    else:
        channels = [filled[..., channel] for channel in range(filled.shape[2])]
        gray = cv2.cvtColor(filled[..., :3], cv2.COLOR_RGB2GRAY)

    foreground = mask > 0
    hole_mask = foreground & (gray <= dark_threshold)
    for channel in channels:
        for col in range(channel.shape[1]):
            fill_line(channel[:, col], hole_mask[:, col], max_gap)
        for row in range(channel.shape[0]):
            fill_line(channel[row, :], hole_mask[row, :], max_gap)
    return filled.astype(image.dtype, copy=False)


def _apply_mask_to_image(image, mask):
    if image.shape[:2] != mask.shape[:2] or image.size == 0:
        return image

    cleaned = image.copy()
    background = mask <= 0
    if cleaned.ndim == 2:
        cleaned[background] = 0
    else:
        cleaned[background, :] = 0
    return cleaned


def _build_gray_display_mask(clean_mask, source_mask):
    if clean_mask.shape[:2] != source_mask.shape[:2] or clean_mask.size == 0:
        return clean_mask

    clean = np.where(clean_mask > 150, 255, 0).astype(np.uint8)
    source = np.where(source_mask > 150, 255, 0).astype(np.uint8)
    if not np.any(source):
        return clean_mask

    height = source.shape[0]
    close_height = max(7, min(31, height // 180))
    if close_height % 2 == 0:
        close_height += 1
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, close_height))
    source = cv2.morphologyEx(source, cv2.MORPH_CLOSE, kernel, iterations=2)
    source = cv2.bitwise_and(source, clean)

    component_count, labels, stats, _ = cv2.connectedComponentsWithStats(
        source, 8)
    if component_count <= 1:
        return clean_mask

    largest_index = max(range(1, component_count),
                        key=lambda index: stats[index, cv2.CC_STAT_AREA])
    largest_area = stats[largest_index, cv2.CC_STAT_AREA]
    if largest_area < np.count_nonzero(clean) * 0.2:
        return clean_mask

    display_mask = np.where(labels == largest_index, 255, 0).astype(np.uint8)
    display_mask = cv2.morphologyEx(display_mask,
                                    cv2.MORPH_CLOSE,
                                    kernel,
                                    iterations=1)
    return display_mask.astype(clean_mask.dtype, copy=False)


def _pad_width_to_bounds(image, current_left, current_right, target_left,
                         target_right):
    if image is None or image.ndim < 2:
        return image

    left_pad = max(int(current_left) - int(target_left), 0)
    right_pad = max(int(target_right) - int(current_right), 0)
    if left_pad == 0 and right_pad == 0:
        return image

    if image.ndim == 2:
        pad_width = ((0, 0), (left_pad, right_pad))
    else:
        pad_width = ((0, 0), (left_pad, right_pad), (0, 0))
    return np.pad(image, pad_width, mode="constant", constant_values=0)


def _align_camera_crops_to_common_bounds(datas):
    valid_bounds = []
    for data in datas:
        crop_rec = data.get("crop_rec")
        if crop_rec and len(crop_rec) >= 4:
            left = int(crop_rec[0])
            right = left + int(crop_rec[2])
        elif data.get("2D") is not None:
            left = 0
            right = int(data["2D"].shape[1])
        else:
            continue
        if right > left:
            valid_bounds.append((left, right))

    if not valid_bounds:
        return datas

    target_left = min(left for left, _ in valid_bounds)
    target_right = max(right for _, right in valid_bounds)
    if target_right <= target_left:
        return datas

    for data in datas:
        crop_rec = data.get("crop_rec")
        if crop_rec and len(crop_rec) >= 4:
            current_left = int(crop_rec[0])
            current_width = int(crop_rec[2])
        else:
            current_left = 0
            current_width = int(data["2D"].shape[1])
        current_right = current_left + current_width
        for key in ("2D", "MASK", "3D", "VALIDITY"):
            image = data.get(key)
            if image is not None:
                data[key] = _pad_width_to_bounds(image, current_left,
                                                 current_right, target_left,
                                                 target_right)
        data["common_crop_rec"] = [
            target_left,
            int(crop_rec[1]) if crop_rec and len(crop_rec) >= 4 else 0,
            target_right - target_left,
            int(crop_rec[3])
            if crop_rec and len(crop_rec) >= 4 else int(data["2D"].shape[0])
        ]
    return datas


def _trim_empty_mask_columns(data):
    mask = data.get("MASK")
    if mask is None or mask.ndim < 2 or mask.size == 0:
        return data

    foreground_columns = np.flatnonzero(np.any(mask > 150, axis=0))
    if foreground_columns.size == 0:
        return data

    left = int(foreground_columns[0])
    right = int(foreground_columns[-1] + 1)
    if left == 0 and right == mask.shape[1]:
        return data

    for key in ("2D", "MASK", "3D", "VALIDITY"):
        image = data.get(key)
        if image is not None and image.ndim >= 2:
            data[key] = image[:, left:right]
    data["empty_column_trim"] = [left, 0, right - left, mask.shape[0]]
    return data


class ImageMosaic(Globs.control.BaseImageMosaic):
    """
    单表面处理
    """

    def __init__(self, config, managerQueue, logger_process: LoggerProcess):
        super().__init__()
        self.daemon = True
        self._running = True
        self.dataFolderList: List[DataFolder] = []
        self.d3Saver: Optional[D3Saver] = None
        self.imageSaver: Optional[ImageSaver] = None
        self.managerQueue = managerQueue
        self.currentSecondaryCoil = None
        self.colorImageDict = {}
        self.loggerProcess = logger_process
        self.config = config
        self.key = config["key"]
        self.saveFolder = Path(config["saveFolder"])
        self.rotate = config["rotate"]
        self.direction = config["direction"]
        self.x_rotate = config["x_rotate"]
        self.queue_put_timeout = _get_mosaic_queue_put_timeout()
        self.result_timeout = _get_mosaic_result_timeout()
        self.save3D_data = bool(config.get("save3D_data", True))
        self.save = True
        self._shutdown_lock = threading.Lock()
        self._workers_stopped = False
        self.saveFolder.mkdir(parents=True, exist_ok=True)
        self.dataList = []
        self.start()

    def setSave(self, save: bool):
        self.save = save

    def _clear_color_images(self) -> None:
        for color_image in self.colorImageDict.values():
            try:
                color_image.close()
            except Exception as e:
                logger.debug("close color image failed surface=%s: %s", self.key, e)
        self.colorImageDict.clear()

    def _save_(self, image, path):
        if self.save:
            queued = self.imageSaver.add(image, path)
            if not queued:
                raise RuntimeError(f"failed to queue image save: {path}")
            return True
        return None

    def set_coil_id(self, coil_id, secondary_coil=None):
        coil_id = str(coil_id)
        self.drain_results()
        if not self.has_data(coil_id):
            return False
        (self.saveFolder / coil_id).mkdir(parents=True, exist_ok=True)
        try:
            self.producer.put(
                {
                    "coil_id": coil_id,
                    "secondary_coil": secondary_coil,
                },
                timeout=self.queue_put_timeout,
            )
            return True
        except Full:
            logger.warning(
                "ImageMosaic producer queue full, drop coil_id=%s surface=%s",
                coil_id, self.key)
        except Exception as e:
            logger.exception(
                "ImageMosaic producer queue put failed coil_id=%s surface=%s: %s",
                coil_id, self.key, e)
        return False

    def _save_image_(self, data_integration, image, name):
        from pathlib import Path

        cache_image = image.copy()

        # 保存 PNG
        self._save_(
            image,
            data_integration.get_save_url(
                "png", name + serverConfigProperty.save_image_type))

        # 保存 JPG（用于缓存生成）
        jpg_path = Path(data_integration.get_save_url("jpg", name + ".jpg"))
        self._save_(image, jpg_path)

        # 保存 MASK PNG
        image_rgba = image.convert("RGBA")
        image_rgba.putalpha(data_integration.pil_mask)
        self._save_(image_rgba,
                    data_integration.get_save_url("mask", name + ".png"))

        # 保存预览
        image = image.copy()
        image.thumbnail(PreviewSize)
        self._save_(image,
                    data_integration.get_save_url("preview", name + ".jpg"))

        # ========== 生成缩略图缓存（在 jpg 目录下） ==========
        try:
            from Base.utils.cache_generator import generate_gray_thumbnail, generate_jet_thumbnail

            coil_id = data_integration.coilId
            surface_key = data_integration.surface

            # 缓存目录：{saveFolder}/{surface_key}/{coil_id}/jpg/cache/
            cache_base = Path(data_integration.get_save_url("jpg",
                                                            "")) / "cache"

            # GRAY 缓存：从 GRAY.jpg 生成
            if name == "GRAY":
                gray_cache_dir = cache_base / "falsecolor" / "gray"
                generate_gray_thumbnail(source_pil_image=cache_image,
                                        cache_dir=gray_cache_dir,
                                        size=1024)
                logger.info("Generated GRAY cache for %s/%s", surface_key,
                            coil_id)

            # JET 缓存：从 JET.jpg 生成（如果 JET 图像存在）
            elif name == "JET":
                jet_cache_dir = cache_base / "falsecolor" / "jet"
                generate_jet_thumbnail(source_pil_image=cache_image,
                                       cache_dir=jet_cache_dir,
                                       size=1024)
                logger.info("Generated JET cache for %s/%s", surface_key,
                            coil_id)

        except Exception as e:
            logger.error("Failed to generate cache for %s: %s", name, e)
        finally:
            cache_image.close()
            image_rgba.close()
            image.close()

    # 保存图像
    async def save_image(self, data_integration: DataIntegration):
        self._save_image_(data_integration, data_integration.pil_image, "GRAY")
        self._save_image_(data_integration, data_integration.pil_mask, "MASK")

    async def save_json(self, data_integration: DataIntegration):
        coil_id = data_integration.coilId
        data = data_integration.export_json()
        payload = json.dumps(data, ensure_ascii=False,
                             indent=4).encode("utf-8")
        atomic_write_bytes(payload, self.saveFolder / coil_id / "data.json")

    async def save3_d(self, data_integration: DataIntegration):
        config_datas = data_integration.configDatas
        circle_config = data_integration.circle_config
        mask_image = data_integration.npy_mask
        coil_id = data_integration.coilId

        start = data_integration.median_non_zero + serverConfigProperty.colorFromValue_mm // data_integration.scan3dCoordinateScaleZ
        self._save_(data_integration.npy_data,
                    self.saveFolder / coil_id / "3D.npz")
        step = (serverConfigProperty.colorToValue_mm -
                serverConfigProperty.colorFromValue_mm
                ) // data_integration.scan3dCoordinateScaleZ
        data_integration.set("colorFromValue_mm",
                             serverConfigProperty.colorFromValue_mm)
        data_integration.set("colorToValue_mm",
                             serverConfigProperty.colorToValue_mm)
        data_integration.set("start", start)
        data_integration.set("step", step)
        self._clear_color_images()
        data_integration.set_telescoped_alarms()
        npy__ = data_integration.npy_data
        a, b = start, start + step
        # Keep the false-colour conversion to one float32 work buffer.  The
        # former expression produced a non-zero copy, a clipped copy and
        # several float64 temporaries at the same time; on a full stitched
        # surface that could temporarily consume several times the image size
        # and leave the native allocator's idle baseline unnecessarily high.
        depth_map_scaled = npy__.astype(np.float32, copy=True)
        np.clip(depth_map_scaled, float(a), float(b), out=depth_map_scaled)
        depth_map_scaled -= float(a)
        color_span = float(b - a)
        if color_span > 0:
            depth_map_scaled *= -255.0 / color_span
            depth_map_scaled += 255.0
        else:
            logger.warning(
                "invalid 3D false-colour range surface=%s coil=%s start=%s step=%s",
                data_integration.key,
                coil_id,
                start,
                step,
            )
            depth_map_scaled.fill(0.0)
        depth_map_uint8 = depth_map_scaled.astype(np.uint8)
        depth_map_scaled = None
        mask_zero = npy__ == 0
        for name, colormap in ColorMaps.items():
            if name not in serverConfigProperty.renderer_list:
                continue
            depth_map_color = cv2.applyColorMap(depth_map_uint8, colormap)
            depth_map_color[mask_zero] = [0, 0, 0]  # [0, 0, 0] 表示黑色

            image = Image.fromarray(depth_map_color)
            try:
                self._save_image_(data_integration, image, name)
            finally:
                # ImageSaver queues its own copies; no reader consumes
                # colorImageDict, so retaining full-resolution renderers until
                # the next coil only inflates the idle memory baseline.
                image.close()
                depth_map_color = None

        # ========== 生成 Error 塔形报警图像 ==========
        try:
            from Base.utils.cache_generator import generate_error_image, get_error_cache_dir

            # 保存 3D.npz 的路径
            npy_file = self.saveFolder / coil_id / "3D.npz"

            # median_z_int 用于计算阈值偏移
            median_z_int = int(data_integration.median_non_zero
                               ) if data_integration.median_non_zero else 0
            threshold_down, threshold_up = self._get_taper_error_thresholds(
                data_integration)

            # png 目录用于保存 Error.png
            png_dir = get_error_cache_dir(str(npy_file))
            generate_error_image(
                npy_data=npy__,
                png_dir=png_dir,
                median_z_int=median_z_int,
                threshold_down=threshold_down,
                threshold_up=threshold_up,
                scale_factor=data_integration.scan3dCoordinateScaleZ)
            logger.info("Generated Error image for %s/%s",
                        data_integration.key, coil_id)
        except Exception as e:
            logger.error("Failed to generate Error image: %s", e)

        obj_file = self.saveFolder / coil_id / "3D.obj"
        if self.save3D_data:
            queued = self.d3Saver.add_([
                coil_id,
                npy__,
                mask_image,
                config_datas,
                circle_config,
                obj_file,
                data_integration.median_3d_mm,
                data_integration.get_bd_xyz(),
                data_integration.scan3dCoordinateOffsetZ,
            ])
            if not queued:
                logger.error("3D mesh save queue failed for %s/%s",
                             data_integration.key, coil_id)
        return None

    def join_saver(self):
        self.imageSaver.join()

    def _get_taper_error_thresholds(self, data_integration: DataIntegration):
        default_threshold = 60
        try:
            from AlarmDetection.property import alarmConfigProperty

            _, height_limits, _, _, _ = alarmConfigProperty.get_taper_shape_config(
                data_integration).get_config().get_config()
            return taper_error_threshold_from_limits(height_limits)
        except Exception as e:
            logger.warning(
                "get taper error thresholds failed, use default %s: %s",
                default_threshold, e)
        return default_threshold, default_threshold

    @DetectionSpeedRecord.timing_decorator("数据获取 __getAllData__")
    def __getAllData__(self, data_integration):
        # 设置 任务
        """
        对于最新的数据，应该同步完成，缺乏实时模式
        Args:
            data_integration:

        Returns:

        """
        self._ensure_source_links(data_integration.coilId)
        frame_plans = self._get_capture_frame_plans(data_integration.coilId)
        for index, dataFolder in enumerate(self.dataFolderList):
            frame_plan = frame_plans[index] if frame_plans is not None else None
            if not dataFolder.set_coil_id(data_integration.coilId, frame_plan):
                self.raise_error(
                    "camera data queue unavailable",
                    coil=data_integration.coilId,
                    surface=self.key,
                    camera=dataFolder.folderName,
                )
        if frame_plans is not None:
            data_integration.set("captureFramePlans", [{
                "camera":
                dataFolder.folderName,
                "stems":
                frame_plan,
                "missingSlots": [
                    index
                    for index, stem in enumerate(frame_plan) if stem is None
                ],
            } for dataFolder, frame_plan in zip(self.dataFolderList,
                                                frame_plans)])
        #  获取数据
        datas = []
        config_datas = []
        deadline = time.monotonic() + self.result_timeout
        for dataFolder in self.dataFolderList:  # 获取所有的图片
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                self.raise_error(
                    "camera data result timeout",
                    coil=data_integration.coilId,
                    surface=self.key,
                    camera=dataFolder.folderName,
                )
            try:
                data = dataFolder.get_data(
                    timeout=remaining,
                    expected_coil_id=data_integration.coilId,
                )
            except (RuntimeError, TimeoutError) as e:
                self.raise_error(
                    "camera data result unavailable",
                    coil=data_integration.coilId,
                    surface=self.key,
                    camera=dataFolder.folderName,
                    detail=str(e),
                )
            datas.append(data)
            try:
                config_datas.append(data["json"])
            except KeyError:
                logger.warning(
                    "config data missing: coil=%s, surface=%s, camera=%s",
                    data_integration.coilId,
                    self.key,
                    dataFolder.folderName,
                )
        #   待修改，使用工具类型进行封装
        data_integration.datas, data_integration.configDatas = datas, config_datas

    def _ensure_source_links(self, coil_id):
        """Create every camera source link before validating capture data."""
        for data_folder in self.dataFolderList:
            try:
                if not data_folder.mk_link(coil_id):
                    logger.error(
                        "capture source link was not created or queued: "
                        "coil=%s surface=%s camera=%s",
                        coil_id,
                        self.key,
                        data_folder.folderName,
                    )
            except Exception as e:
                logger.exception(
                    "capture source link creation failed: "
                    "coil=%s surface=%s camera=%s error=%s",
                    coil_id,
                    self.key,
                    getattr(data_folder, "folderName", None),
                    e,
                )

    def _get_capture_frame_plans(self, coil_id):
        frame_sequences = []
        for dataFolder in self.dataFolderList:
            try:
                frames = dataFolder.get_capture_frames(str(coil_id))
            except Exception as e:
                logger.warning(
                    "get capture frames failed: coil=%s, surface=%s, camera=%s, error=%s",
                    coil_id,
                    self.key,
                    dataFolder.folderName,
                    e,
                )
                return None
            if not frames:
                logger.warning(
                    "no capture frames: coil=%s, surface=%s, camera=%s",
                    coil_id,
                    self.key,
                    dataFolder.folderName,
                )
                return None
            frame_sequences.append(frames)

        try:
            frame_plans = align_capture_frame_sequences(frame_sequences)
        except ValueError as e:
            self.raise_error(
                "capture frame alignment failed",
                coil=coil_id,
                surface=self.key,
                detail=str(e),
            )
        for dataFolder, frame_plan in zip(self.dataFolderList, frame_plans):
            missing_slots = [
                index for index, stem in enumerate(frame_plan) if stem is None
            ]
            if missing_slots:
                logger.error(
                    "capture frame gap preserved: coil=%s, surface=%s, camera=%s, missing_slots=%s, stems=%s",
                    coil_id,
                    self.key,
                    dataFolder.folderName,
                    missing_slots,
                    frame_plan,
                )
        return frame_plans

    def _get_common_capture_stems(self, coil_id):
        capture_stem_lists = []
        for dataFolder in self.dataFolderList:
            try:
                stems = dataFolder.get_capture_stems(str(coil_id))
            except Exception as e:
                logger.warning(
                    "get capture stems failed: coil=%s, surface=%s, camera=%s, error=%s",
                    coil_id,
                    self.key,
                    dataFolder.folderName,
                    e,
                )
                return None
            if not stems:
                logger.warning(
                    "no capture stems: coil=%s, surface=%s, camera=%s",
                    coil_id, self.key, dataFolder.folderName)
                return None
            capture_stem_lists.append([str(stem) for stem in stems])

        capture_stem_sets = [set(stems) for stems in capture_stem_lists]
        common = set.intersection(
            *capture_stem_sets) if capture_stem_sets else set()
        common_stems = [
            stem for stem in capture_stem_lists[0] if stem in common
        ] if capture_stem_lists else []
        if len(common_stems) < 2:
            logger.warning(
                "too few common capture stems: coil=%s, surface=%s, stems=%s",
                coil_id, self.key, common_stems)
            return None
        logger.warning(
            "use common capture stems: coil=%s, surface=%s, stems=%s", coil_id,
            self.key, common_stems)
        return common_stems

    def raise_error(self, message, **context):
        raise ServerDetectionException(message, context=context)

    @DetectionSpeedRecord.timing_decorator("拼接图像计时")
    def __stitching__(self, data_integration: DataIntegration):
        min_h = None
        max_h = None
        valid_datas = []
        datas = data_integration.datas
        for data in datas:
            camera = data.get("camera", "unknown")
            missing_keys = [
                key for key in ["2D", "MASK", "3D"]
                if key not in data or data[key] is None
            ]
            if missing_keys:
                logger.warning(
                    "skip camera data with missing keys: coil=%s, surface=%s, camera=%s, missing=%s",
                    data_integration.coilId,
                    data_integration.surface,
                    camera,
                    missing_keys,
                )
                continue
            validity = data.get("VALIDITY")
            if validity is None or validity.shape[:2] != data["MASK"].shape[:2]:
                data["VALIDITY"] = np.full(data["MASK"].shape[:2],
                                           255,
                                           dtype=np.uint8)
            if any(data[key].size == 0 for key in ["2D", "MASK", "3D"]):
                logger.warning(
                    "skip camera data with empty image: coil=%s, surface=%s, camera=%s, shapes=%s",
                    data_integration.coilId,
                    data_integration.surface,
                    camera,
                    {
                        "2D": data["2D"].shape,
                        "MASK": data["MASK"].shape,
                        "3D": data["3D"].shape
                    },
                )
                continue

            image_h = data["2D"].shape[0]
            rec = data.get("rec")
            if rec and len(rec) >= 4 and rec[3] > 0:
                top = max(0, int(rec[1]))
                bottom = min(image_h, top + int(rec[3]))
            else:
                logger.warning(
                    "steel rect missing, use full image height: coil=%s, surface=%s, camera=%s, crop_rec=%s",
                    data_integration.coilId,
                    data_integration.surface,
                    camera,
                    data.get("crop_rec"),
                )
                top = 0
                bottom = image_h
            if bottom <= top:
                logger.warning(
                    "invalid crop range, use full image height: coil=%s, surface=%s, camera=%s, top=%s, bottom=%s",
                    data_integration.coilId,
                    data_integration.surface,
                    camera,
                    top,
                    bottom,
                )
                top = 0
                bottom = image_h
            min_h = top if min_h is None else min(min_h, top)
            max_h = bottom if max_h is None else max(max_h, bottom)
            valid_datas.append(data)

        if not valid_datas or min_h is None or max_h is None or max_h <= min_h:
            self.raise_error(
                "no valid camera data",
                coil=data_integration.coilId,
                surface=data_integration.surface,
            )

        datas = valid_datas
        _align_camera_crops_to_common_bounds(datas)
        out_side_px = Globs.control.out_side_px
        crop_top = max(min_h - out_side_px, 0)
        crop_datas = []
        for data in datas:  # 裁剪，减低计算
            camera = data.get("camera", "unknown")
            camera = data.get("camera", "unknown")
            crop_bottom = min(max_h + out_side_px, data["2D"].shape[0])
            if crop_bottom <= crop_top:
                logger.warning(
                    "skip camera data after crop: coil=%s, surface=%s, camera=%s, crop_top=%s, crop_bottom=%s",
                    data_integration.coilId,
                    data_integration.surface,
                    camera,
                    crop_top,
                    crop_bottom,
                )
                continue
            for key in ["2D", "MASK", "3D", "VALIDITY"]:
                data[key] = data[key][crop_top:crop_bottom, :]
            if data["MASK"].size == 0 or not np.any(data["MASK"] > 150):
                logger.warning(
                    "skip camera data with empty mask foreground: coil=%s, surface=%s, camera=%s, mask_shape=%s",
                    data_integration.coilId,
                    data_integration.surface,
                    camera,
                    data["MASK"].shape,
                )
                continue
            _trim_empty_mask_columns(data)
            crop_datas.append(data)

        if not crop_datas:
            self.raise_error(
                "no valid mask after crop",
                coil=data_integration.coilId,
                surface=data_integration.surface,
            )

        datas = crop_datas
        data_integration.datas = datas
        camera_plane_alignments = align_camera_depth_planes(
            datas,
            data_integration.scan3dCoordinateScaleZ,
            data_integration.scan3dCoordinateOffsetZ,
        )
        if camera_plane_alignments:
            data_integration.set("cameraPlaneAlignments",
                                 camera_plane_alignments)
            logger.info(
                "aligned camera 3D planes: coil=%s, surface=%s, adjustments=%s",
                data_integration.coilId,
                data_integration.surface,
                camera_plane_alignments,
            )
        horizontal_projection_list = tool.get_horizontal_projection_list(
            [data["MASK"] for data in datas])
        cross_points = tool.find_cross_points(horizontal_projection_list)
        data_integration.set_cross_points(cross_points)

        min_height = min([data["2D"].shape[0] for data in datas])
        for index in range(len(datas)):
            datas[index]['2D'] = datas[index]['2D'][:min_height, :]
            datas[index]['MASK'] = datas[index]['MASK'][:min_height, :]
            datas[index]['3D'] = datas[index]['3D'][:min_height, :]
            datas[index]['VALIDITY'] = datas[index]['VALIDITY'][:min_height, :]

        leveling_2d(datas)
        level_camera_boundaries(datas, cross_points, self.direction)
        join_image, join_mask_image, join_validity = feather_camera_images(
            datas, cross_points, self.direction)

        # Camera depths are first converted to the reference Z calibration, then
        # edge-aligned so adjacent camera seams stay on the same plane.
        depth_images = prepare_camera_depths_for_join(datas, cross_points,
                                                      self.direction)
        npy_data = tool.hstack_3d(depth_images,
                                  join_mask_image=join_mask_image)

        quarter_turns = 0
        if self.rotate == 90 or data_integration.surface == "S":
            quarter_turns += 1
            join_image = np.rot90(join_image, 1)
            join_mask_image = np.rot90(join_mask_image, 1)
            join_validity = np.rot90(join_validity, 1)
            npy_data = np.rot90(npy_data, 1)
            join_image = cv2.flip(join_image, 1)
            join_mask_image = cv2.flip(join_mask_image, 1)
            join_validity = cv2.flip(join_validity, 1)
            npy_data = cv2.flip(npy_data, 1)

        if self.rotate == -90 or data_integration.surface == "L":
            quarter_turns -= 1
            join_image = np.rot90(join_image, -1)
            join_mask_image = np.rot90(join_mask_image, -1)
            join_validity = np.rot90(join_validity, -1)
            npy_data = np.rot90(npy_data, -1)

        if quarter_turns % 2:
            # Image columns/rows exchange roles in a quarter-turn. All later
            # measurements and meshes operate in the rotated image frame.
            scale_x = getattr(data_integration, "scan3dCoordinateScaleX", None)
            scale_y = getattr(data_integration, "scan3dCoordinateScaleY", None)
            if scale_x is not None and scale_y is not None:
                data_integration.set("scan3dCoordinateScaleX", scale_y)
                data_integration.set("scan3dCoordinateScaleY", scale_x)

        box = tool.crop_black_border(join_mask_image)
        x, y, w, h = box
        data_integration.set("rotate", self.rotate)
        data_integration.set("crop_box", box)
        join_mask_image = join_mask_image[y:y + h, x:x + w]
        join_image = join_image[y:y + h, x:x + w]
        join_validity = join_validity[y:y + h, x:x + w]
        npy_data = npy_data[y:y + h, x:x + w]
        source_mask_image = join_mask_image.copy()
        join_mask_image = _clean_annulus_mask(join_mask_image)
        clean_box = tool.crop_black_border(join_mask_image)
        clean_x, clean_y, clean_w, clean_h = clean_box
        data_integration.set("clean_crop_box", clean_box)
        if (clean_x, clean_y, clean_w,
                clean_h) != (0, 0, join_mask_image.shape[1],
                             join_mask_image.shape[0]):
            join_mask_image = join_mask_image[clean_y:clean_y + clean_h,
                                              clean_x:clean_x + clean_w]
            join_image = join_image[clean_y:clean_y + clean_h,
                                    clean_x:clean_x + clean_w]
            join_validity = join_validity[clean_y:clean_y + clean_h,
                                          clean_x:clean_x + clean_w]
            npy_data = npy_data[clean_y:clean_y + clean_h,
                                clean_x:clean_x + clean_w]
            source_mask_image = source_mask_image[clean_y:clean_y + clean_h,
                                                  clean_x:clean_x + clean_w]
        join_mask_image = cv2.bitwise_and(join_mask_image, join_validity)
        source_mask_image = cv2.bitwise_and(source_mask_image, join_validity)
        data_integration.set("missingCapturePixels",
                             int(np.count_nonzero(join_validity == 0)))
        gray_display_mask = _build_gray_display_mask(join_mask_image,
                                                     source_mask_image)
        join_image = _fill_masked_gray_gaps(join_image, join_mask_image)
        join_image = _apply_mask_to_image(join_image, gray_display_mask)
        npy_data = _fill_masked_zero_gaps(npy_data, join_mask_image)
        npy_data[join_mask_image == 0] = 0
        if np.max(join_mask_image.shape) < control.minMaskDetectErrorSize:
            self.raise_error(
                "mask too small for detection",
                coil=data_integration.coilId,
                surface=data_integration.surface,
                mask_shape=join_mask_image.shape,
                min_size=control.minMaskDetectErrorSize,
            )
        data_integration.joinImage = join_image

        data_integration.npy_image = join_image
        data_integration.pil_image = Image.fromarray(join_image)

        data_integration.npy_mask = join_mask_image
        data_integration.pil_mask = Image.fromarray(join_mask_image)
        data_integration.set_npy_data(npy_data)

        return join_image, join_mask_image, npy_data

    @DetectionSpeedRecord.timing_decorator("图像保持")
    def sync_save(self, data_integration):
        return asyncio.run(self.save_all_data(data_integration))

    async def save_all_data(self, data_integration: DataIntegration):
        await self.save_image(data_integration)
        await self.save3_d(data_integration)
        if self.save and not self.imageSaver.flush():
            raise RuntimeError(
                f"image save failed or timed out: {data_integration.surface}/{data_integration.coilId}"
            )
        await self.save_json(data_integration)

    def run(self):
        try:
            self._run()
        finally:
            self._shutdown_workers()

    def _run(self):
        # 拼接后的主函数
        startup_activity = runtime_heartbeat.begin_activity(
            "3d_surface_initialization",
            self.key,
        )
        try:
            self.imageSaver = ImageSaver(self.managerQueue, self.loggerProcess)
            self.d3Saver = D3Saver(self.managerQueue, self.loggerProcess)
            self.dataFolderList = []
            for folderConfig in self.config["folderList"]:
                fd_dt = [
                    folderConfig, self.config["saveFolder"],
                    self.config["direction"]
                ]
                self.dataFolderList.append(
                    DataFolder(fd_dt, self.loggerProcess.get_logger()))
        finally:
            runtime_heartbeat.end_activity(startup_activity)
        while self._running:
            work_item = self.producer.get()
            if work_item is None:
                break
            if isinstance(work_item, dict):
                coil_id = str(work_item["coil_id"])
                current_secondary_coil = work_item.get("secondary_coil")
            else:
                coil_id = str(work_item)
                current_secondary_coil = self.currentSecondaryCoil
            activity = runtime_heartbeat.begin_activity(
                f"3d_surface_{self.key}",
                coil_id,
            )
            data_integration = DataIntegration(coil_id, self.saveFolder,
                                               self.direction, self.key)
            try:
                logger.info("ImageMosaic %s %s", self.key,
                            data_integration.coilId)
                total_start = time.perf_counter()
                get_data_start = time.perf_counter()
                self.__getAllData__(data_integration)  # 获取全部的拼接数据
                get_data_s = time.perf_counter() - get_data_start
                original_start = time.perf_counter()
                data_integration.set_original_data(data_integration.datas)
                original_s = time.perf_counter() - original_start
                # 裁剪 2D 3D MASK
                stitch_start = time.perf_counter()
                self.__stitching__(data_integration)
                stitch_s = time.perf_counter() - stitch_start
                data_integration.currentSecondaryCoil = current_secondary_coil
                save_start = time.perf_counter()
                self.sync_save(data_integration)
                save_s = time.perf_counter() - save_start
                # Thread(target=self.sync_save, args=(data_integration,)).start()
                # self.sync_save(data_integration)
                # AlarmDetection.detection(data_integration)

                # AlarmDetection.detectionAll(data_integration)

                commit_start = time.perf_counter()
                data_integration.commit()
                commit_s = time.perf_counter() - commit_start
                logger.info(
                    "perf ImageMosaic coil=%s surface=%s get_data_s=%.3f set_original_s=%.3f "
                    "stitch_s=%.3f save_s=%.3f commit_s=%.3f total_s=%.3f",
                    coil_id,
                    self.key,
                    get_data_s,
                    original_s,
                    stitch_s,
                    save_s,
                    commit_s,
                    time.perf_counter() - total_start,
                )
            except ServerDetectionException as e:
                error_msg = str(e)
                data_integration.processing_error = error_msg
                logger.warning(
                    "ImageMosaic detection error coil=%s surface=%s: %s",
                    data_integration.coilId,
                    self.key,
                    error_msg,
                )
                data_integration.add_server_detection_error(error_msg)
                logger.warning(
                    "ImageMosaic recovered after detection error, continue server"
                )
            except Exception as e:
                data_integration.processing_error = f"unexpected mosaic error: {e}"
                logger.exception("Error in ImageMosaic %s",
                                 data_integration.coilId)
                if isLoc and Globs.control.debug_raise:
                    raise

            finally:
                try:
                    self.consumer.put(data_integration,
                                      timeout=self.queue_put_timeout)
                except Full:
                    logger.warning(
                        "ImageMosaic consumer queue full, drop result coil_id=%s surface=%s",
                        getattr(data_integration, "coilId", None),
                        self.key,
                    )
                except Exception as e:
                    logger.exception(
                        "ImageMosaic consumer queue put failed coil_id=%s surface=%s: %s",
                        getattr(data_integration, "coilId", None),
                        self.key,
                        e,
                    )
                finally:
                    runtime_heartbeat.end_activity(activity)
                    # The consumer queue now owns this result. This thread can
                    # otherwise pin the entire stitched coil while idle in the
                    # next producer.get().
                    data_integration = None
                    work_item = None
                    current_secondary_coil = None

    def _shutdown_workers(self):
        with self._shutdown_lock:
            if self._workers_stopped:
                return
            for data_folder in self.dataFolderList:
                try:
                    data_folder.stop()
                except Exception as e:
                    logger.exception(
                        "DataFolder stop failed: surface=%s camera=%s: %s",
                        self.key,
                        getattr(data_folder, "folderName", None),
                        e,
                    )
            for data_folder in self.dataFolderList:
                try:
                    data_folder.join(timeout=5)
                    if data_folder.is_alive():
                        logger.warning(
                            "DataFolder did not stop: surface=%s camera=%s",
                            self.key,
                            getattr(data_folder, "folderName", None),
                        )
                except Exception as e:
                    logger.exception(
                        "DataFolder join failed: surface=%s camera=%s: %s",
                        self.key,
                        getattr(data_folder, "folderName", None),
                        e,
                    )
            if self.imageSaver:
                try:
                    self.imageSaver.join()
                except Exception as e:
                    logger.exception("ImageSaver shutdown failed: %s", e)
            if self.d3Saver:
                try:
                    self.d3Saver.join()
                except Exception as e:
                    logger.exception("D3Saver shutdown failed: %s", e)
            self._clear_color_images()
            self._workers_stopped = True

    def request_stop(self):
        self._running = False
        # 退出 run 循环
        try:
            self.producer.put(None, timeout=self.queue_put_timeout)
        except Full:
            logger.warning("ImageMosaic stop signal queue full surface=%s",
                           self.key)
        except Exception as e:
            logger.exception(
                "ImageMosaic stop signal put failed surface=%s: %s", self.key,
                e)
        # 停止工作进程/线程
    def stop(self):
        self.request_stop()
        if threading.current_thread() is self:
            return
        saver_timeout = 0.0
        if self.imageSaver is not None:
            saver_timeout = (self.imageSaver.flush_timeout +
                             self.imageSaver.join_timeout *
                             max(self.imageSaver.num_processes, 1))
        shutdown_timeout = max(self.result_timeout + saver_timeout + 30.0,
                               60.0)
        self.join(timeout=shutdown_timeout)
        if self.is_alive():
            logger.warning(
                "ImageMosaic graceful shutdown still in progress: surface=%s timeout=%ss",
                self.key,
                shutdown_timeout,
            )
            return
        self._shutdown_workers()

    def drain_results(self):
        dropped = 0
        while True:
            try:
                stale = self.consumer.get_nowait()
            except Empty:
                break
            dropped += 1
            logger.warning(
                "drop stale mosaic result before request: surface=%s coil_id=%s",
                self.key,
                getattr(stale, "coilId", None),
            )
        return dropped

    def get_data(self, timeout=None, expected_coil_id=None):
        if timeout is None:
            timeout = self.result_timeout
        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(
                    f"ImageMosaic result timeout surface={self.key} "
                    f"coil={expected_coil_id} timeout={timeout}s")
            try:
                result = self.consumer.get(timeout=remaining)
            except Empty:
                raise TimeoutError(
                    f"ImageMosaic result timeout surface={self.key} "
                    f"coil={expected_coil_id} timeout={timeout}s")
            if (expected_coil_id is None or str(getattr(result, "coilId", ""))
                    == str(expected_coil_id)):
                return result
            logger.warning(
                "drop mismatched mosaic result: surface=%s expected=%s actual=%s",
                self.key,
                expected_coil_id,
                getattr(result, "coilId", None),
            )

    def has_folder(self, coil_id):
        """
        文件夹是否存在
        Args:
            coil_id:

        Returns:

        """
        for folderConfig in self.config["folderList"]:
            if not DataFolder.static_has_data(Path(folderConfig["source"]),
                                              coil_id):
                return False
        return True

    def check_detection_end(self, coil_id):
        for folderConfig in self.config["folderList"]:
            if not DataFolder.static_check_detection_end(
                    Path(folderConfig["source"]), coil_id):
                return False
        return True

    def has_data(self, coil_id):
        return self.has_folder(coil_id)
