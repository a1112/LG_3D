import importlib
import sys
import types
from pathlib import Path
from queue import Queue
from types import SimpleNamespace

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
    align_camera_depth_planes, depth_to_reference_units,
    get_camera_z_calibration,
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
        "camera":
        "Cap_L_U",
        "3D":
        np.array([[0, 100]], dtype=np.uint16),
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


def test_camera_depth_calibration_skips_leading_missing_slot():
    camera = {
        "json": [{}, {
            "bdConfig": {
                "CoordinateC": {
                    "Scan3dCoordinateScale": 0.25,
                    "Scan3dCoordinateOffset": 10.0,
                }
            }
        }]
    }

    assert get_camera_z_calibration(camera) == (0.25, 10.0)


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
        "camera":
        name,
        "2D":
        np.full((120, 3), 80, dtype=np.uint8),
        "MASK":
        np.full((120, 3), 255, dtype=np.uint8),
        "3D":
        np.full((120, 3), raw_depth, dtype=np.uint16),
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


def test_get_data_discards_result_from_previous_coil(monkeypatch):
    image_mosaic_module = _load_light_image_mosaic_module(monkeypatch)
    mosaic = image_mosaic_module.ImageMosaic.__new__(
        image_mosaic_module.ImageMosaic)
    mosaic.consumer = Queue()
    mosaic.key = "S"
    mosaic.result_timeout = 1
    mosaic.consumer.put(SimpleNamespace(coilId="old"))
    expected = SimpleNamespace(coilId="new")
    mosaic.consumer.put(expected)

    assert mosaic.get_data(expected_coil_id="new") is expected


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
    mosaic.raise_error = lambda message: (_ for _ in
                                          ()).throw(AssertionError(message))

    _, _, stitched_depth = mosaic.__stitching__(data_integration)

    assert stitched_depth.dtype == np.uint16
    assert np.unique(stitched_depth[stitched_depth > 0]).tolist() == [5000]
    assert data_integration.npy_data_value is stitched_depth
    assert len(data_integration.dictData["cameraPlaneAlignments"]) == 2
    assert {
        item["camera"]
        for item in data_integration.dictData["cameraPlaneAlignments"]
    } == {"cam_a", "cam_c"}


def test_depth_overlap_falls_back_to_camera_with_valid_capture(monkeypatch):
    image_mosaic_module = _load_light_image_mosaic_module(monkeypatch)
    monkeypatch.setattr(image_mosaic_module.serverConfigProperty,
                        "max_clip_mun", 3000)
    left_depth = np.array([[100, 0], [100, 100]], dtype=np.uint16)
    right_depth = np.array([[200, 200], [200, 200]], dtype=np.uint16)
    datas = [{
        "3D": left_depth,
        "MASK": np.full((2, 2), 255, dtype=np.uint8),
        "VALIDITY": np.array([[255, 0], [255, 255]], dtype=np.uint8),
    }, {
        "3D": right_depth,
        "MASK": np.full((2, 2), 255, dtype=np.uint8),
        "VALIDITY": np.full((2, 2), 255, dtype=np.uint8),
    }]

    depth_images = image_mosaic_module.prepare_camera_depths_for_join(
        datas, [(0, 1)], "R")
    joined = np.hstack(depth_images)

    assert joined.tolist() == [[100, 200, 200], [100, 100, 200]]


def test_clean_annulus_mask_removes_thin_seams_and_inner_noise(monkeypatch):
    image_mosaic_module = _load_light_image_mosaic_module(monkeypatch)
    mask = np.zeros((220, 220), dtype=np.uint8)
    yy, xx = np.indices(mask.shape)
    outer = (xx - 110)**2 + (yy - 110)**2 <= 95**2
    inner = (xx - 110)**2 + (yy - 110)**2 <= 40**2
    mask[outer & ~inner] = 255
    mask[105:108, :] = 0
    mask[inner & (xx < 110) & (yy > 90)] = 255

    clean = image_mosaic_module._clean_annulus_mask(mask)

    assert clean[105:108, 35:65].min() == 255
    assert clean[105:108, 155:185].min() == 255
    assert clean[110, 110] == 0
    assert clean[130, 95] == 0


def test_clean_annulus_mask_recovers_hole_connected_to_outer_background(
        monkeypatch):
    image_mosaic_module = _load_light_image_mosaic_module(monkeypatch)
    mask = np.zeros((500, 500), dtype=np.uint8)
    yy, xx = np.indices(mask.shape)
    outer = (xx - 250)**2 + (yy - 250)**2 <= 220**2
    inner = (xx - 250)**2 + (yy - 250)**2 <= 85**2
    mask[outer & ~inner] = 255

    # Simulate a missing camera band that opens the center hole to the
    # background. The old component fit turns this into a giant vertical oval.
    mask[250:, 225:276] = 0

    clean = image_mosaic_module._clean_annulus_mask(mask)
    contours, _ = image_mosaic_module.cv2.findContours(
        image_mosaic_module.cv2.bitwise_not(clean),
        image_mosaic_module.cv2.RETR_LIST,
        image_mosaic_module.cv2.CHAIN_APPROX_SIMPLE,
    )
    centered = []
    for contour in contours:
        x, y, width, height = image_mosaic_module.cv2.boundingRect(contour)
        if abs(x + width / 2 - 250) < 15 and abs(y + height / 2 - 250) < 15:
            centered.append((width, height))

    assert centered
    hole_width, hole_height = min(centered,
                                  key=lambda size: abs(size[0] - 170))
    assert 155 <= hole_width <= 190
    assert 155 <= hole_height <= 190
    assert clean[430, 250] == 255


def test_circle_config_recovers_hole_connected_to_outer_background():
    mask = np.zeros((500, 500), dtype=np.uint8)
    yy, xx = np.indices(mask.shape)
    outer = (xx - 250)**2 + (yy - 250)**2 <= 220**2
    inner = (xx - 250)**2 + (yy - 250)**2 <= 85**2
    mask[outer & ~inner] = 255
    mask[250:, 225:276] = 0

    ellipse = tool.get_circle_config_by_mask(mask)["inner_circle"]["ellipse"]
    (center_x, center_y), (width, height), _ = ellipse

    assert abs(center_x - 250) < 10
    assert abs(center_y - 250) < 10
    assert 155 <= width <= 190
    assert 155 <= height <= 190


def test_fill_masked_zero_gaps_interpolates_internal_depth_seam(monkeypatch):
    image_mosaic_module = _load_light_image_mosaic_module(monkeypatch)
    depth = np.full((7, 7), 3000, dtype=np.uint16)
    depth[3, 1:6] = 0
    mask = np.full((7, 7), 255, dtype=np.uint8)

    filled = image_mosaic_module._fill_masked_zero_gaps(depth, mask)

    assert np.all(filled[3, 1:6] == 3000)


def test_fill_masked_zero_gaps_handles_camera_boundary_band(monkeypatch):
    image_mosaic_module = _load_light_image_mosaic_module(monkeypatch)
    depth = np.full((32, 24), 3000, dtype=np.uint16)
    depth[11:20, 4:20] = 0
    mask = np.full((32, 24), 255, dtype=np.uint8)

    filled = image_mosaic_module._fill_masked_zero_gaps(depth,
                                                        mask,
                                                        iterations=16)

    assert np.all(filled[11:20, 4:20] == 3000)


def test_fill_masked_gray_gaps_interpolates_thin_camera_seam(monkeypatch):
    image_mosaic_module = _load_light_image_mosaic_module(monkeypatch)
    image = np.full((24, 16), 120, dtype=np.uint8)
    image[9:13, 2:14] = 0
    mask = np.full((24, 16), 255, dtype=np.uint8)

    filled = image_mosaic_module._fill_masked_gray_gaps(image, mask, max_gap=8)

    assert np.all(filled[9:13, 2:14] == 120)


def test_fill_masked_gray_gaps_keeps_large_dark_region(monkeypatch):
    image_mosaic_module = _load_light_image_mosaic_module(monkeypatch)
    image = np.full((24, 16), 120, dtype=np.uint8)
    image[5:20, 2:14] = 0
    mask = np.full((24, 16), 255, dtype=np.uint8)

    filled = image_mosaic_module._fill_masked_gray_gaps(image, mask, max_gap=8)

    assert np.all(filled[5:20, 2:14] == 0)


def test_apply_mask_to_image_clears_background(monkeypatch):
    image_mosaic_module = _load_light_image_mosaic_module(monkeypatch)
    image = np.full((4, 5), 120, dtype=np.uint8)
    mask = np.zeros((4, 5), dtype=np.uint8)
    mask[1:3, 2:4] = 255

    cleaned = image_mosaic_module._apply_mask_to_image(image, mask)

    assert cleaned[0, 0] == 0
    assert np.all(cleaned[1:3, 2:4] == 120)


def test_build_gray_display_mask_removes_disconnected_noise(monkeypatch):
    image_mosaic_module = _load_light_image_mosaic_module(monkeypatch)
    clean = np.zeros((80, 80), dtype=np.uint8)
    source = np.zeros((80, 80), dtype=np.uint8)
    clean[10:70, 10:70] = 255
    source[20:60, 20:60] = 255
    source[65:72, 65:72] = 255

    display = image_mosaic_module._build_gray_display_mask(clean, source)

    assert display[30, 30] == 255
    assert display[68, 68] == 0


def test_align_camera_crops_uses_union_bounds(monkeypatch):
    image_mosaic_module = _load_light_image_mosaic_module(monkeypatch)
    datas = [
        {
            "2D": np.ones((2, 4), dtype=np.uint8),
            "MASK": np.ones((2, 4), dtype=np.uint8) * 255,
            "3D": np.ones((2, 4), dtype=np.uint16),
            "crop_rec": [10, 0, 4, 2],
        },
        {
            "2D": np.ones((2, 6), dtype=np.uint8) * 2,
            "MASK": np.ones((2, 6), dtype=np.uint8) * 255,
            "3D": np.ones((2, 6), dtype=np.uint16) * 2,
            "crop_rec": [8, 0, 6, 2],
        },
        {
            "2D": np.ones((2, 7), dtype=np.uint8) * 3,
            "MASK": np.ones((2, 7), dtype=np.uint8) * 255,
            "3D": np.ones((2, 7), dtype=np.uint16) * 3,
            "crop_rec": [9, 0, 7, 2],
        },
    ]

    image_mosaic_module._align_camera_crops_to_common_bounds(datas)

    assert [data["2D"].shape[1] for data in datas] == [8, 8, 8]
    assert datas[0]["2D"][:, :2].max() == 0
    assert datas[0]["2D"][:, 2:6].min() == 1
    assert datas[0]["2D"][:, 6:].max() == 0
    assert datas[2]["2D"][:, 1:].min() == 3
    assert all(data["common_crop_rec"] == [8, 0, 8, 2] for data in datas)


def test_trim_empty_mask_columns_keeps_foreground_bounds(monkeypatch):
    image_mosaic_module = _load_light_image_mosaic_module(monkeypatch)
    data = {
        "2D": np.tile(np.arange(8, dtype=np.uint8), (3, 1)),
        "MASK": np.zeros((3, 8), dtype=np.uint8),
        "3D": np.tile(np.arange(8, dtype=np.uint16), (3, 1)),
    }
    data["MASK"][:, 2:6] = 255

    image_mosaic_module._trim_empty_mask_columns(data)

    assert data["2D"].shape == (3, 4)
    assert data["2D"][0].tolist() == [2, 3, 4, 5]
    assert data["3D"][0].tolist() == [2, 3, 4, 5]
    assert data["empty_column_trim"] == [2, 0, 4, 3]


def test_common_stems_use_capture_frames_not_3d_validity(monkeypatch):
    image_mosaic_module = _load_light_image_mosaic_module(monkeypatch)

    class FakeFolder:
        folderName = "fake"

        def get_capture_stems(self, coil_id):
            return [str(index) for index in range(11)]

        def get_valid_3d_stems(self, coil_id):
            return ["1", "2", "3", "4", "5"]

    mosaic = image_mosaic_module.ImageMosaic.__new__(
        image_mosaic_module.ImageMosaic)
    mosaic.key = "L"
    mosaic.dataFolderList = [FakeFolder(), FakeFolder(), FakeFolder()]

    stems = mosaic._get_common_capture_stems("206074")

    assert stems == [str(index) for index in range(11)]


def test_common_stems_keep_reference_camera_capture_order(monkeypatch):
    image_mosaic_module = _load_light_image_mosaic_module(monkeypatch)

    class FakeFolder:

        def __init__(self, name, stems):
            self.folderName = name
            self.stems = stems

        def get_capture_stems(self, coil_id):
            return self.stems

    mosaic = image_mosaic_module.ImageMosaic.__new__(
        image_mosaic_module.ImageMosaic)
    mosaic.key = "S"
    mosaic.dataFolderList = [
        FakeFolder("reference", ["8", "9", "0", "1"]),
        FakeFolder("middle", ["0", "1", "8", "9"]),
        FakeFolder("last", ["9", "8", "1", "0"]),
    ]

    stems = mosaic._get_common_capture_stems("test-coil")

    assert stems == ["8", "9", "0", "1"]


def test_stitching_keeps_missing_capture_slot_out_of_final_mask(monkeypatch):
    image_mosaic_module = _load_light_image_mosaic_module(monkeypatch)
    monkeypatch.setattr(image_mosaic_module.Globs.control, "out_side_px", 0)
    monkeypatch.setattr(image_mosaic_module.Globs.control, "leveling_gray",
                        False)
    monkeypatch.setattr(image_mosaic_module.control, "minMaskDetectErrorSize",
                        1)
    monkeypatch.setattr(image_mosaic_module, "_clean_annulus_mask",
                        lambda mask: mask.copy())

    data = _camera_data("camera-with-gap",
                        raw_depth=3000,
                        scale_z=1.0,
                        offset_z=0.0)
    data["VALIDITY"] = np.full(data["MASK"].shape, 255, dtype=np.uint8)
    data["VALIDITY"][40:80, :] = 0
    data["2D"][40:80, :] = 0
    data["3D"][40:80, :] = 0
    integration = FakeStitchDataIntegration([data])
    mosaic = image_mosaic_module.ImageMosaic.__new__(
        image_mosaic_module.ImageMosaic)
    mosaic.rotate = 0
    mosaic.direction = "R"
    mosaic.raise_error = lambda message, **context: (_ for _ in ()).throw(
        AssertionError((message, context)))

    gray, mask, depth = mosaic.__stitching__(integration)

    assert np.all(mask[40:80, :] == 0)
    assert np.all(gray[40:80, :] == 0)
    assert np.all(depth[40:80, :] == 0)


def test_feather_camera_images_replaces_hard_overlap_seam(monkeypatch):
    image_mosaic_module = _load_light_image_mosaic_module(monkeypatch)

    def camera(value):
        return {
            "2D": np.full((3, 8), value, dtype=np.uint8),
            "MASK": np.full((3, 8), 255, dtype=np.uint8),
            "VALIDITY": np.full((3, 8), 255, dtype=np.uint8),
        }

    image, mask, validity = image_mosaic_module.feather_camera_images(
        [camera(50), camera(150)], [(4, 4)], "L")

    assert image.shape == (3, 12)
    assert image[0].tolist() == [
        50, 50, 50, 50, 50, 83, 117, 150, 150, 150, 150, 150
    ]
    assert np.max(np.abs(np.diff(image[0].astype(np.int16)))) < 100
    assert np.all(mask == 255)
    assert np.all(validity == 255)


def test_level_camera_boundaries_matches_outer_cameras_per_row(monkeypatch):
    image_mosaic_module = _load_light_image_mosaic_module(monkeypatch)
    monkeypatch.setattr(image_mosaic_module.Globs.control, "leveling_gray",
                        True)

    def camera(value):
        return {
            "2D": np.full((120, 16), value, dtype=np.uint8),
            "MASK": np.full((120, 16), 255, dtype=np.uint8),
            "VALIDITY": np.full((120, 16), 255, dtype=np.uint8),
        }

    datas = [camera(50), camera(100), camera(150)]

    image_mosaic_module.level_camera_boundaries(datas, [(0, 0), (0, 0)],
                                                "L",
                                                band_width=8)

    assert [int(np.median(data["2D"])) for data in datas] == [100, 100, 100]
