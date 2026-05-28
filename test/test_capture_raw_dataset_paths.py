import os
import sys
import time
from pathlib import Path

import numpy as np
import pytest
from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "app" / "algorithm_runtime"))

from SplicingService.capture_paths import (  # noqa: E402
    capture_complete,
    resolve_capture_dir,
    sorted_indexed_files,
)


def test_resolve_capture_dir_accepts_lowercase_raw_capture_layout(tmp_path):
    source = tmp_path / "Cap_S_U"
    expected = source / "193113" / "2d"
    expected.mkdir(parents=True)

    assert resolve_capture_dir(source, "193113", ("2D", "2d")) == expected


def test_capture_complete_accepts_old_jpg_files_in_lowercase_2d_dir(tmp_path):
    source = tmp_path / "Cap_S_U"
    image_dir = source / "193113" / "2d"
    image_dir.mkdir(parents=True)
    old_time = time.time() - 10
    for index in range(4):
        image_path = image_dir / f"{index}.jpg"
        image_path.write_bytes(b"fake")
        os.utime(image_path, (old_time, old_time))

    assert capture_complete(source, "193113", quiet_seconds=3.2) is True


def test_capture_complete_rejects_recent_files(tmp_path):
    source = tmp_path / "Cap_S_U"
    image_dir = source / "193113" / "2d"
    image_dir.mkdir(parents=True)
    for index in range(4):
        (image_dir / f"{index}.jpg").write_bytes(b"fake")

    assert capture_complete(source, "193113", quiet_seconds=3.2) is False


def test_sorted_indexed_files_orders_numeric_stems(tmp_path):
    for name in ("10.jpg", "2.jpg", "1.bmp"):
        (tmp_path / name).write_bytes(b"fake")

    assert [path.name for path in sorted_indexed_files(tmp_path, ("*.jpg", "*.bmp"))] == [
        "1.bmp",
        "2.jpg",
        "10.jpg",
    ]


@pytest.mark.skipif(
    not (PROJECT_ROOT / "TestData" / "from").exists(),
    reason="local raw capture dataset is not present",
)
def test_local_from_dataset_has_expected_camera_layout():
    dataset = PROJECT_ROOT / "TestData" / "from"
    expected_cameras = {
        "Cap_L_D",
        "Cap_L_M",
        "Cap_L_U",
        "Cap_S_D",
        "Cap_S_M",
        "Cap_S_U",
    }

    assert {path.name for path in dataset.iterdir() if path.is_dir()} == expected_cameras
    for camera in expected_cameras:
        coil_dir = dataset / camera / "193113"
        assert (coil_dir / "json").exists()
        assert resolve_capture_dir(dataset / camera, "193113", ("2D", "2d")).name == "2d"
        assert resolve_capture_dir(dataset / camera, "193113", ("3D", "3d")).name == "3d"
        assert len(sorted_indexed_files(coil_dir / "json", ("*.json",))) == 11
        assert len(sorted_indexed_files(coil_dir / "2d", ("*.jpg", "*.bmp"))) == 11
        assert len(sorted_indexed_files(coil_dir / "3d", ("*.npz", "*.npy"))) == 11


@pytest.mark.skipif(
    not (PROJECT_ROOT / "TestData" / "from").exists(),
    reason="local raw capture dataset is not present",
)
def test_local_from_dataset_sample_files_are_readable():
    dataset = PROJECT_ROOT / "TestData" / "from"
    for camera_dir in sorted(path for path in dataset.iterdir() if path.is_dir()):
        coil_dir = camera_dir / "193113"
        image_path = sorted_indexed_files(coil_dir / "2d", ("*.jpg", "*.bmp"))[0]
        npz_path = sorted_indexed_files(coil_dir / "3d", ("*.npz", "*.npy"))[0]

        with Image.open(image_path) as image:
            assert image.size == (2560, 1024)

        with np.load(npz_path) as data:
            assert "array" in data.files
            assert data["array"].shape == (1024, 2560)
            assert data["array"].dtype == np.uint16
