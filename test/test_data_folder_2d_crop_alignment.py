import asyncio
import sys
from pathlib import Path

import numpy as np
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[1]
for path in (
        PROJECT_ROOT / "app",
        PROJECT_ROOT / "app" / "Base",
        PROJECT_ROOT / "app" / "algorithm_runtime",
):
    path_text = str(path)
    if path_text not in sys.path:
        sys.path.insert(0, path_text)

from SplicingService.DataFolder import DataFolder  # noqa: E402
from SplicingService.DataFolder import tool as data_folder_tool  # noqa: E402
import Base.property.Base as base_property  # noqa: E402
from Base.property.Base import DataIntegration  # noqa: E402


def test_capture_source_link_is_created_before_camera_data_is_loaded(
        tmp_path, monkeypatch):
    folder = DataFolder.__new__(DataFolder)
    folder.saveFolder = tmp_path / "Save_S"
    folder.source = tmp_path / "Cap_S_M"
    folder.folderName = "Cap_S_M"
    created = {}

    def create_link(link_path, target, target_is_directory=False):
        created["link"] = link_path
        created["target"] = target
        created["target_is_directory"] = target_is_directory

    monkeypatch.setattr(Path, "symlink_to", create_link)

    assert folder.mk_link("217565") is True
    assert created == {
        "link": tmp_path / "Save_S" / "217565" / "link" / "Cap_S_M",
        "target": tmp_path / "Cap_S_M" / "217565",
        "target_is_directory": True,
    }


def test_2d_crop_rec_controls_gray_mask_and_depth():
    gray = np.tile(np.arange(12, dtype=np.uint8), (6, 1))
    mask = np.zeros((6, 12), dtype=np.uint8)
    mask[:, 4:8] = 255
    depth = np.zeros((6, 12), dtype=np.uint16)
    depth[:, 1:11] = 3000

    crop_rec, crop_gray, crop_mask, crop_depth = DataFolder._crop_aligned_by_2d_rec(
        gray,
        mask,
        depth,
        [4, 0, 4, 6],
    )

    assert crop_rec == [4, 0, 4, 6]
    assert crop_gray.shape == (6, 4)
    assert crop_mask.shape == (6, 4)
    assert crop_depth.shape == (6, 4)
    assert crop_gray[0].tolist() == [4, 5, 6, 7]
    assert np.all(crop_mask == 255)
    assert np.all(crop_depth == 3000)


def test_3d_valid_columns_do_not_expand_2d_crop_or_mask():
    gray = np.zeros((5, 10), dtype=np.uint8)
    mask = np.zeros((5, 10), dtype=np.uint8)
    mask[:, 4:6] = 255
    depth = np.zeros((5, 10), dtype=np.uint16)
    depth[:, 1:9] = 3000

    crop_rec, _, crop_mask, crop_depth = DataFolder._crop_aligned_by_2d_rec(
        gray,
        mask,
        depth,
        [4, 0, 2, 5],
    )

    assert crop_rec == [4, 0, 2, 5]
    assert crop_mask.shape == (5, 2)
    assert crop_depth.shape == (5, 2)
    assert np.count_nonzero(crop_mask) == 10


def test_load_camera_frames_preserves_missing_time_slot(tmp_path, monkeypatch):
    coil_id = "42"
    image_dir = tmp_path / coil_id / "2d"
    depth_dir = tmp_path / coil_id / "3d"
    image_dir.mkdir(parents=True)
    depth_dir.mkdir(parents=True)
    Image.fromarray(np.full((2, 3), 10,
                            dtype=np.uint8)).save(image_dir / "1.bmp")
    Image.fromarray(np.full((2, 3), 30,
                            dtype=np.uint8)).save(image_dir / "3.bmp")
    np.savez_compressed(depth_dir / "1.npz",
                        array=np.full((2, 3), 100, dtype=np.uint16))
    np.savez_compressed(depth_dir / "3.npz",
                        array=np.full((2, 3), 300, dtype=np.uint16))

    folder = DataFolder.__new__(DataFolder)
    folder.source = tmp_path
    folder.folderName = "test-camera"
    folder.direction = "L"
    folder.cropLeft = 0
    folder.cropRight = 0
    monkeypatch.setattr(
        data_folder_tool,
        "get_foreground",
        lambda image, direction, folder_name:
        (image, np.full(image.shape, 255, dtype=np.uint8)),
    )
    monkeypatch.setattr(
        data_folder_tool,
        "crop_max_image_black_edges",
        lambda folder_name, mask, crop: [0, 0, mask.shape[1], mask.shape[0]],
    )

    gray, mask, _, validity = asyncio.run(
        folder.load2_d(coil_id, ["1", None, "3"]))
    depth = asyncio.run(folder.load3_d(coil_id, ["1", None, "3"], []))

    assert gray[:, 0].tolist() == [10, 10, 0, 0, 30, 30]
    assert mask[:, 0].tolist() == [255, 255, 0, 0, 255, 255]
    assert validity[:, 0].tolist() == [255, 255, 0, 0, 255, 255]
    assert depth[:, 0].tolist() == [100, 100, 0, 0, 300, 300]


def test_original_metadata_skips_leading_missing_slot(tmp_path, monkeypatch):

    class Axis:
        scan3dCoordinateScale = 0.25
        scan3dCoordinateOffset = 10

    class FakeBdData:

        def __init__(self, _config):
            self.bdDataX = Axis()
            self.bdDataY = Axis()
            self.bdDataZ = Axis()

    monkeypatch.setattr(base_property, "BdData", FakeBdData)
    integration = DataIntegration("42", tmp_path, "L", "L")

    integration.set_original_data([{
        "camera":
        "Cap_L_D",
        "json": [{}, {
            "bdConfig": {
                "valid": True
            },
            "coilData": {
                "Weight": 5
            },
        }],
    }])

    assert integration.scan3dCoordinateScaleZ == 0.25
    assert integration.scan3dCoordinateOffsetZ == 10
    assert integration.use == 5
