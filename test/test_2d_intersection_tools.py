import sys
from pathlib import Path

import numpy as np
import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = PROJECT_ROOT / "app"
ALG_2D_ROOT = PROJECT_ROOT / "app" / "algorithm_runtime_2D"
for path in (APP_ROOT, ALG_2D_ROOT):
    path_text = str(path)
    if path_text not in sys.path:
        sys.path.insert(0, path_text)

from algorithm_runtime_2D.JoinService import cv_count_tool  # noqa: E402


def test_get_max_contour_intersections_keeps_first_and_last_pixel_per_row():
    image = np.zeros((4, 6), dtype=np.uint8)
    image[1, 2:5] = 255
    image[3, 0] = 255

    _, intersections = cv_count_tool.get_max_contour_and_intersections(image)

    assert intersections == [[1, 2], [1, 4], [3, 0]]


def test_get_the_difference_int_uses_right_median_when_larger():
    value = cv_count_tool.get_the_difference_int(
        ([11, 12, 13, 14, 15], [50, 51, 52, 53, 54])
    )

    assert value == 52


def test_hconcat_list_handles_zero_intersections_without_recursion():
    images = [
        np.full((2, 4, 3), 10, dtype=np.uint8),
        np.full((2, 4, 3), 20, dtype=np.uint8),
        np.full((2, 4, 3), 30, dtype=np.uint8),
    ]

    result = cv_count_tool.hconcat_list(images, [0, 0])

    assert result.shape == (2, 12, 3)


def test_hconcat_list_normalizes_height_and_dtype_before_opencv():
    images = [
        np.full((4, 3), 10, dtype=np.uint8),
        np.full((5, 3), 20, dtype=np.float64),
    ]

    result = cv_count_tool.hconcat_list(images, [0])

    assert result.shape == (4, 6)
    assert result.dtype == np.uint8


def test_hconcat_list_preserves_normalized_float_intensity_when_casting_to_uint8():
    images = [
        np.zeros((2, 2), dtype=np.uint8),
        np.ones((2, 2), dtype=np.float32),
    ]

    result = cv_count_tool.hconcat_list(images, [0])

    assert np.all(result[:, 2:] == 255)


def test_hconcat_list_rejects_overlap_count_mismatch():
    images = [
        np.zeros((2, 3), dtype=np.uint8),
        np.zeros((2, 3), dtype=np.uint8),
    ]

    with pytest.raises(ValueError, match="overlap count mismatch"):
        cv_count_tool.hconcat_list(images, [])


def test_hconcat_list_clamps_invalid_overlap_values():
    images = [np.zeros((2, 4), dtype=np.uint8) for _ in range(3)]

    result = cv_count_tool.hconcat_list(images, [-10, 99])

    assert result.shape == (2, 12)


def test_debug_image_show_is_disabled_by_default():
    assert cv_count_tool._get_image_show_thread() is None
    assert cv_count_tool.CONFIG.enable_image_show is False
    assert cv_count_tool.CONFIG.image_show_wait_ms >= 1
