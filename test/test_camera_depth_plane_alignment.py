import importlib
import sys
import types
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
for path in (
        PROJECT_ROOT / "app",
        PROJECT_ROOT / "app" / "Base",
        PROJECT_ROOT / "app" / "algorithm_runtime",
):
    path_text = str(path)
    if path_text not in sys.path:
        sys.path.insert(0, path_text)

from Base.tools import tool  # noqa: E402
from SplicingService.depth_plane import (  # noqa: E402
    align_camera_depth_planes,
    depth_to_reference_units,
)


def test_depth_to_reference_units_uses_z_scale_offset_and_keeps_zero():
    depth = np.array([[0, 100], [110, 0]], dtype=np.uint16)

    aligned = depth_to_reference_units(
        depth,
        source_scale=2.0,
        source_offset=10.0,
        reference_scale=1.0,
        reference_offset=0.0,
    )

    assert aligned.dtype == np.uint16
    assert aligned.tolist() == [[0, 210], [230, 0]]


def test_align_camera_depth_planes_reads_camera_json_calibration():
    datas = [{
        "camera": "Cap_L_U",
        "3D": np.array([[0, 100]], dtype=np.uint16),
        "json": [{
            "bdConfig": {
                "CoordinateC": {
                    "Scan3dCoordinateScale": 2.0,
                    "Scan3dCoordinateOffset": 10.0,
                }
            }
        }],
    }]

    adjustments = align_camera_depth_planes(
        datas,
        reference_scale=1.0,
        reference_offset=0.0,
    )

    assert datas[0]["3D"].tolist() == [[0, 210]]
    assert adjustments[0]["camera"] == "Cap_L_U"
    assert adjustments[0]["rawOffsetToReference"] == 10.0


def test_hstack_3d_edge_alignment_preserves_invalid_zero_pixels():
    left = np.array(
        [
            [0, 3000, 3000],
            [0, 3000, 3000],
            [0, 3000, 3000],
            [0, 3000, 3000],
        ],
        dtype=np.uint16,
    )
    right = np.array(
        [
            [5000, 5000, 0],
            [5000, 5000, 0],
            [5000, 5000, 0],
            [5000, 5000, 0],
        ],
        dtype=np.uint16,
    )

    result = tool.hstack_3d([left, right], window_size=2, max_blocks=1)

    assert result.dtype == np.uint16
    assert np.all(result[:, 3:5] == 3000)
    assert np.all(result[:, 5] == 0)


def _camera_data(name, raw_depth, scale_z, offset_z):
    return {
        "camera": name,
        "2D": np.full((120, 3), 80, dtype=np.uint8),
        "MASK": np.full((120, 3), 255, dtype=np.uint8),
        "3D": np.full((120, 3), raw_depth, dtype=np.uint16),
        "rec": [0, 0, 3, 120],
        "json": [{
            "bdConfig": {
                "CoordinateC": {
                    "Scan3dCoordinateScale": scale_z,
                    "Scan3dCoordinateOffset": offset_z,
                }
            }
        }],
    }


class FakeStitchDataIntegration:
    coilId = "test-coil"
    surface = "X"
    key = "X"
    scan3dCoordinateScaleZ = 1.0
    scan3dCoordinateOffsetZ = 0.0

    def __init__(self, datas):
        self.datas = datas
        self.dictData = {}
        self.crossPoints = []
        self.npy_data_value = None

    def set(self, key, value):
        self.dictData[key] = value
        setattr(self, key, value)

    def set_cross_points(self, cross_points):
        self.crossPoints = cross_points

    def set_npy_data(self, npy_data):
        self.npy_data_value = npy_data


def _load_light_image_mosaic_module(monkeypatch):
    class DummyWorkerBase:
        def __init__(self, *args, **kwargs):
            pass

        def start(self):
            pass

    fake_control = types.SimpleNamespace(
        BaseImageMosaic=DummyWorkerBase,
        BaseDataFolder=DummyWorkerBase,
        out_side_px=0,
        leveling_gray=False,
        minMaskDetectErrorSize=1,
    )
    fake_globs = types.ModuleType("Globs")
    fake_globs.control = fake_control

    fake_save_module = types.ModuleType("Save3D.save")
    fake_save_module.D3Saver = object
    fake_save_package = types.ModuleType("Save3D")
    fake_save_package.save = fake_save_module

    fake_data_folder_module = types.ModuleType("SplicingService.DataFolder")
    fake_data_folder_module.DataFolder = object
    fake_image_saver_module = types.ModuleType("SplicingService.ImageSaver")
    fake_image_saver_module.ImageSaver = object

    monkeypatch.setitem(sys.modules, "Globs", fake_globs)
    monkeypatch.setitem(sys.modules, "Base.Globs", fake_globs)
    monkeypatch.setitem(sys.modules, "Save3D", fake_save_package)
    monkeypatch.setitem(sys.modules, "Save3D.save", fake_save_module)
    monkeypatch.setitem(sys.modules, "SplicingService.DataFolder",
                        fake_data_folder_module)
    monkeypatch.setitem(sys.modules, "SplicingService.ImageSaver",
                        fake_image_saver_module)

    base_package = importlib.import_module("Base")
    monkeypatch.setattr(base_package, "Globs", fake_globs, raising=False)
    sys.modules.pop("SplicingService.ImageMosaic", None)
    return importlib.import_module("SplicingService.ImageMosaic")


def test_image_mosaic_stitching_aligns_camera_depth_planes(monkeypatch):
    image_mosaic_module = _load_light_image_mosaic_module(monkeypatch)
    monkeypatch.setattr(image_mosaic_module.Globs.control, "out_side_px", 0)
    monkeypatch.setattr(image_mosaic_module.Globs.control, "leveling_gray",
                        False)
    monkeypatch.setattr(image_mosaic_module.control, "minMaskDetectErrorSize",
                        1)
    monkeypatch.setattr(image_mosaic_module.serverConfigProperty,
                        "max_clip_mun", 3000)

    data_integration = FakeStitchDataIntegration([
        _camera_data("cam_a", raw_depth=2000, scale_z=2.0, offset_z=1000.0),
        _camera_data("cam_b", raw_depth=5000, scale_z=1.0, offset_z=0.0),
        _camera_data("cam_c", raw_depth=8000, scale_z=0.5, offset_z=1000.0),
    ])
    mosaic = image_mosaic_module.ImageMosaic.__new__(
        image_mosaic_module.ImageMosaic)
    mosaic.rotate = 0
    mosaic.direction = "R"
    mosaic.raise_error = lambda message: (_ for _ in ()).throw(
        AssertionError(message)
    )

    _, _, stitched_depth = mosaic.__stitching__(data_integration)

    assert stitched_depth.dtype == np.uint16
    assert np.unique(stitched_depth[stitched_depth > 0]).tolist() == [5000]
    assert data_integration.npy_data_value is stitched_depth
    assert len(data_integration.dictData["cameraPlaneAlignments"]) == 2
    assert {
        item["camera"]
        for item in data_integration.dictData["cameraPlaneAlignments"]
    } == {"cam_a", "cam_c"}
