import sys
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
for path in (PROJECT_ROOT, PROJECT_ROOT / "app"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from Base.tools import tool  # noqa: E402


def test_crop_black_border_returns_nonzero_bounds():
    image = np.zeros((5, 7), dtype=np.uint8)
    image[1:4, 2:6] = 255

    assert tool.crop_black_border(image) == (2, 1, 4, 3)


def test_crop_black_border_all_black_uses_full_image():
    image = np.zeros((3, 4), dtype=np.uint8)

    assert tool.crop_black_border(image) == (0, 0, 4, 3)


def test_crop_black_border_supports_color_arrays():
    image = np.zeros((4, 5, 3), dtype=np.float32)
    image[1:3, 2:5, 1] = 1.5

    assert tool.crop_black_border(image) == (2, 1, 3, 2)


def test_show_image_is_disabled_by_default(monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("OpenCV image window should not open by default")

    monkeypatch.delenv("LG3D_DEBUG_IMAGE_SHOW", raising=False)
    monkeypatch.setattr(tool.cv2, "imshow", fail_if_called)

    assert tool.showImage(np.zeros((2, 2), dtype=np.uint8)) is False


def test_get_foreground_accepts_missing_key():
    image = np.zeros((80, 80), dtype=np.uint8)
    image[:, :30] = 255

    gray, mask = tool.get_foreground(image, direction="R", key=None)

    assert gray.shape == image.shape
    assert mask.shape == image.shape


def test_crop_max_image_black_edges_handles_zero_crop_on_small_image():
    image = np.zeros((8, 12), dtype=np.uint8)
    image[:, :] = 255

    assert tool.crop_max_image_black_edges("L", image, [0, 0]) == [0, 0, 12, 8]


def test_crop_max_image_black_edges_all_black_uses_full_image():
    image = np.zeros((6, 9), dtype=np.uint8)

    assert tool.crop_max_image_black_edges("L", image, [0, 0]) == [0, 0, 9, 6]


def test_auto_crop_accepts_color_image():
    image = np.zeros((80, 80, 3), dtype=np.uint8)
    image[:, :35, :] = 255

    cropped, mask, rec = tool.auto_crop("L", image, [0, 0], "L")

    assert cropped.ndim == 3
    assert mask.ndim == 2
    assert rec[2] > 0


def test_get_circle_config_by_mask_all_foreground_uses_fallback():
    mask = np.full((10, 12), 255, dtype=np.uint8)

    config = tool.get_circle_config_by_mask(mask)

    assert config["inner_circle"]["circlex"] == [6, 5, 5]


def test_get_circle_config_by_mask_handles_small_contour():
    mask = np.full((10, 10), 255, dtype=np.uint8)
    mask[2:4, 2:4] = 0

    config = tool.get_circle_config_by_mask(mask)

    assert "ellipse" in config["inner_circle"]
