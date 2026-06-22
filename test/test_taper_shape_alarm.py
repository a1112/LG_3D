import sys
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "app", ROOT / "app" / "Base", ROOT / "app" / "algorithm_runtime"):
    sys.path.insert(0, str(path))

from AlarmDetection.Configs.TaperShapeConfig import TaperShapeConfig, normalize_taper_height_limits
from AlarmDetection.Configs.AlarmConfigProperty import AlarmConfigProperty
from AlarmDetection.Result.GradResult import AlarmGradResult
from AlarmDetection.Result.AlarmData import AlarmData
import AlarmDetection.Result.AlarmData as alarm_data_module
from SplicingService.taper_error_threshold import taper_error_threshold_from_limits
from Base.utils.cache_generator import generate_error_image
from Base.property.Data3D import LineData, find_line_max_min, valid_line_height_mask
from Base.property.Types import DetectionTaperShapeType, Point2D
import AlarmDetection.Grading.CoilGrading as coil_grading
import AlarmDetection.Grading.alarm_taper_shape as taper_grading
import AlarmDetection.DataProcessing.TaperShape as taper_processing
import AlarmDetection.DataProcessing.TaperShapeLine as taper_line


class FakeDataIntegration:
    coilId = 1001
    surface = "S"
    median_3d_mm = 60.0
    alarmData = SimpleNamespace(lineDataDict={})
    next_code = "2"
    currentSecondaryCoil = SimpleNamespace(Thickness=0)
    scan3dCoordinateScaleX = 1.0
    scan3dCoordinateScaleY = 1.0

    def z_to_mm(self, z):
        return 10.0 + 0.5 * float(z)

    def x_to_mm(self, value):
        return float(value) * self.scan3dCoordinateScaleX


def _point(x, y, z):
    return SimpleNamespace(x=x, y=y, z=float(z))


class FakeAlarmData:
    def __init__(self, center):
        self.flatRollData = SimpleNamespace(get_center=lambda: center)
        self.lineDataDict = None
        self.taper_shape_disabled = False

    def set_line_data_dict(self, line_data):
        self.lineDataDict = line_data


def test_data_integration_next_code_decodes_current_secondary_coil_weight():
    from Base.property.Base import DataIntegration

    data_integration = object.__new__(DataIntegration)
    data_integration.currentSecondaryCoil = SimpleNamespace(Weight=50.0)
    data_integration.coilData = None

    assert data_integration.next_code == "2"


def test_data_integration_next_code_falls_back_to_coil_data_weight():
    from Base.property.Base import DataIntegration

    data_integration = object.__new__(DataIntegration)
    data_integration.currentSecondaryCoil = None
    data_integration.coilData = {"Weight": "50.0"}

    assert data_integration.next_code == "2"


def test_data_integration_next_code_skips_bad_current_weight_for_coil_data():
    from Base.property.Base import DataIntegration

    data_integration = object.__new__(DataIntegration)
    data_integration.currentSecondaryCoil = SimpleNamespace(Weight="bad")
    data_integration.coilData = {"Weight": "50.0"}

    assert data_integration.next_code == "2"


def test_data_integration_next_code_returns_string_default_on_missing_weight(monkeypatch):
    from Base.property.Base import DataIntegration
    import Base.property.Base as base_module

    warnings = []
    data_integration = object.__new__(DataIntegration)
    data_integration.coilId = 1001
    data_integration.direction = "R"
    data_integration.key = "S"
    data_integration.currentSecondaryCoil = SimpleNamespace(Weight="bad")
    data_integration.coilData = {}
    monkeypatch.setattr(base_module.logger, "warning", warnings.append)

    assert data_integration.next_code == "1"
    assert len(warnings) == 1
    assert "next_code" in warnings[0]


def test_taper_shape_config_uses_next_code_override():
    config = TaperShapeConfig({
        "Base": {"name": "base", "height": [60, 80], "inner": 0, "outer": 0, "info": "base"},
        "2": {"name": "code2", "height": [50, 70], "inner": 3, "outer": 1, "info": "code2"},
    }, FakeDataIntegration())

    assert config.get_config().get_config() == ("code2", [50, 70], 3, 1, "code2")


def test_taper_shape_config_normalizes_next_code_variants():
    config_data = {
        "Base": {"name": "base", "height": [60, 80], "inner": 0, "outer": 0, "info": "base"},
        "2": {"name": "code2", "height": [50, 70], "inner": 3, "outer": 1, "info": "code2"},
    }

    for next_code in (2, 2.0, " 2 ", "2.0", b"2"):
        config = TaperShapeConfig(config_data, SimpleNamespace(next_code=next_code))

        assert config.get_config().get_config() == ("code2", [50, 70], 3, 1, "code2")


def test_taper_shape_config_accepts_ascii_encoded_next_code():
    config_data = {
        "Base": {"name": "base", "height": [60, 80], "inner": 0, "outer": 0, "info": "base"},
        "2": {"name": "code2", "height": [50, 70], "inner": 3, "outer": 1, "info": "code2"},
    }

    for next_code in (50, 50.0, "50"):
        config = TaperShapeConfig(config_data, SimpleNamespace(next_code=next_code))

        assert config.get_config().get_config() == ("code2", [50, 70], 3, 1, "code2")


def test_taper_shape_config_accepts_common_next_code_aliases():
    config_data = {
        "Base": {"name": "base", "height": [60, 80], "inner": 0, "outer": 0, "info": "base"},
        "2": {"name": "code2", "height": [50, 70], "inner": 3, "outer": 1, "info": "code2"},
    }

    for data_integration in (
            SimpleNamespace(nextCode="2"),
            SimpleNamespace(NextCode="2"),
            {"nextCode": "2"},
            {"NextCode": "2"},
    ):
        config = TaperShapeConfig(config_data, data_integration)

        assert config.get_config().get_config() == ("code2", [50, 70], 3, 1, "code2")


def test_taper_shape_config_prefers_next_code_alias_over_failure_default():
    class NextCodeAliasData:
        NextCode = "2"

        @property
        def next_code(self):
            return 49

    config = TaperShapeConfig({
        "Base": {"name": "base", "height": [60, 80], "inner": 0, "outer": 0, "info": "base"},
        "49": {"name": "bad49", "height": [30], "inner": 0, "outer": 0, "info": "bad49"},
        "1": {"name": "bad1", "height": [40], "inner": 0, "outer": 0, "info": "bad1"},
        "2": {"name": "code2", "height": [50, 70], "inner": 3, "outer": 1, "info": "code2"},
    }, NextCodeAliasData())

    assert config.get_config().get_config() == ("code2", [50, 70], 3, 1, "code2")


def test_taper_shape_config_prefers_exact_next_code_before_numeric_normalization():
    config = TaperShapeConfig({
        "Base": {"name": "base", "height": [60, 80], "inner": 0, "outer": 0, "info": "base"},
        "02": {"name": "code02", "height": [40], "inner": 1, "outer": 0, "info": "code02"},
        "2": {"name": "code2", "height": [50, 70], "inner": 3, "outer": 1, "info": "code2"},
    }, SimpleNamespace(next_code="02"))

    assert config.get_config().get_config() == ("code02", [40], 1, 0, "code02")


def test_taper_shape_config_prefers_exact_numeric_key_before_ascii_decode():
    config = TaperShapeConfig({
        "Base": {"name": "base", "height": [60, 80], "inner": 0, "outer": 0, "info": "base"},
        "50": {"name": "code50", "height": [45], "inner": 2, "outer": 0, "info": "code50"},
        "2": {"name": "code2", "height": [50, 70], "inner": 3, "outer": 1, "info": "code2"},
    }, SimpleNamespace(next_code=50))

    assert config.get_config().get_config() == ("code50", [45], 2, 0, "code50")


def test_alarm_config_property_uses_default_taper_shape_config_when_missing():
    config_property = object.__new__(AlarmConfigProperty)
    config_property.config = {}

    config = config_property.get_taper_shape_config(FakeDataIntegration())

    assert config.get_config().get_config() == ("默认判断规则", [60, 80], 0, 0, "")


def test_coil_grading_continues_taper_when_flat_roll_grading_fails(monkeypatch):
    taper_calls = []
    add_calls = []
    warnings = []
    data_integration = SimpleNamespace(
        coilId=1001,
        key="S",
        next_code="2",
        next_name="next",
    )

    def bad_flat_roll(_data_integration):
        raise ValueError("bad flat roll data")

    def good_taper(_data_integration):
        taper_calls.append(_data_integration)
        return AlarmGradResult(3, "taper alarm", "")

    def normal_loose(_data_integration):
        return AlarmGradResult(1, "", "")

    monkeypatch.setattr(coil_grading, "grading_alarm_flat_roll", bad_flat_roll)
    monkeypatch.setattr(coil_grading, "grading_alarm_taper_shape", good_taper)
    monkeypatch.setattr(coil_grading, "grading_alarm_loose_coil", normal_loose)
    monkeypatch.setattr(coil_grading.logger, "warning", warnings.append)
    monkeypatch.setattr("CoilDataBase.Coil.add_obj", add_calls.append)

    coil_grading.grading(data_integration)

    assert taper_calls == [data_integration]
    assert len(add_calls) == 1
    alarm_info = add_calls[0]
    assert alarm_info.flatRollGrad == 3
    assert "bad flat roll data" in alarm_info.flatRollMsg
    assert alarm_info.taperShapeGrad == 3
    assert alarm_info.taperShapeMsg == "taper alarm"
    assert alarm_info.grad == 3
    assert len(warnings) == 1


def test_alarm_data_commit_accepts_missing_taper_line_data(monkeypatch):
    flat_roll_commits = []
    add_calls = []
    alarm_data = AlarmData(FakeDataIntegration())
    alarm_data.flatRollData = SimpleNamespace(commit=lambda: flat_roll_commits.append(True))
    alarm_data.lineDataDict = None
    monkeypatch.setattr(alarm_data_module.Alarm, "addObj", add_calls.append)

    alarm_data.commit()

    assert flat_roll_commits == [True]
    assert add_calls == []


def test_alarm_data_commit_skips_invalid_taper_line_data(monkeypatch):
    class BadLineData:
        def line_data_model(self, data_integration):
            raise ValueError("bad taper line")

    class GoodLineData:
        def line_data_model(self, data_integration):
            return "line_model"

        def all_point_data_model(self, data_integration):
            return ["point_model"]

    flat_roll_commits = []
    add_calls = []
    alarm_data = AlarmData(FakeDataIntegration())
    alarm_data.flatRollData = SimpleNamespace(commit=lambda: flat_roll_commits.append(True))
    alarm_data.lineDataDict = {
        "bad": BadLineData(),
        "good": GoodLineData(),
    }
    monkeypatch.setattr(alarm_data_module.Alarm, "addObj", add_calls.append)

    alarm_data.commit()

    assert flat_roll_commits == [True]
    assert add_calls == [["line_model", "point_model"]]


def test_alarm_data_commit_accepts_missing_flat_roll_data(monkeypatch):
    class GoodLineData:
        def line_data_model(self, data_integration):
            return "line_model"

        def all_point_data_model(self, data_integration):
            return ["point_model"]

    warnings = []
    add_calls = []
    alarm_data = AlarmData(FakeDataIntegration())
    alarm_data.lineDataDict = {0: GoodLineData()}
    monkeypatch.setattr(alarm_data_module.Alarm, "addObj", add_calls.append)
    monkeypatch.setattr(alarm_data_module.logger, "warning", warnings.append)

    alarm_data.commit()

    assert add_calls == [["line_model", "point_model"]]
    assert len(warnings) == 1
    assert "missing flat roll data" in warnings[0]


def test_alarm_data_commit_continues_after_invalid_flat_roll_data(monkeypatch):
    class BadFlatRollData:
        def commit(self):
            raise ValueError("bad flat roll")

    class GoodLineData:
        def line_data_model(self, data_integration):
            return "line_model"

        def all_point_data_model(self, data_integration):
            return ["point_model"]

    warnings = []
    add_calls = []
    alarm_data = AlarmData(FakeDataIntegration())
    alarm_data.flatRollData = BadFlatRollData()
    alarm_data.lineDataDict = {0: GoodLineData()}
    monkeypatch.setattr(alarm_data_module.Alarm, "addObj", add_calls.append)
    monkeypatch.setattr(alarm_data_module.logger, "warning", warnings.append)

    alarm_data.commit()

    assert add_calls == [["line_model", "point_model"]]
    assert len(warnings) == 1
    assert "bad flat roll" in warnings[0]


def test_alarm_data_commit_skips_non_finite_taper_model_values(monkeypatch):
    line_data = LineData(
        npy_data=np.zeros((1, 5), dtype=np.int32),
        mask_image=np.ones((1, 5), dtype=np.uint8) * 255,
        p1=Point2D(0, 0),
        p2=Point2D(4, 0),
    )
    line_data._ray_data_ = np.array([
        [0, 0, 100],
        [1, 0, 100],
        [2, 0, 100],
        [3, 0, 100],
        [4, 0, 100],
    ], dtype=float)
    line_data.rotation_angle = 0
    line_data.inner_min_point = _point(0, 0, 100)
    line_data.inner_max_point = _point(1, 0, 100)
    line_data.outer_min_point = _point(3, 0, 100)
    line_data.outer_max_point = _point(4, 0, 100)

    flat_roll_commits = []
    add_calls = []
    data_integration = SimpleNamespace(
        secondary_coil_id=1001,
        key="S",
        width=5,
        height=1,
        median_3d_mm=100.0,
        z_to_mm=lambda z: np.inf,
    )
    alarm_data = AlarmData(data_integration)
    alarm_data.flatRollData = SimpleNamespace(
        commit=lambda: flat_roll_commits.append(True),
        get_center=lambda: Point2D(2, 0),
    )
    alarm_data.lineDataDict = {0: line_data}
    data_integration.alarmData = alarm_data
    monkeypatch.setattr(alarm_data_module.Alarm, "addObj", add_calls.append)

    alarm_data.commit()

    assert flat_roll_commits == [True]
    assert add_calls == []


def test_alarm_data_commit_accepts_sequence_taper_line_data(monkeypatch):
    class GoodLineData:
        def line_data_model(self, data_integration):
            return "line_model"

        def all_point_data_model(self, data_integration):
            return ["point_model"]

    flat_roll_commits = []
    add_calls = []
    alarm_data = AlarmData(FakeDataIntegration())
    alarm_data.flatRollData = SimpleNamespace(commit=lambda: flat_roll_commits.append(True))
    alarm_data.lineDataDict = [GoodLineData()]
    monkeypatch.setattr(alarm_data_module.Alarm, "addObj", add_calls.append)

    alarm_data.commit()

    assert flat_roll_commits == [True]
    assert add_calls == [["line_model", "point_model"]]


def test_taper_shape_detection_and_grading_synthetic_surface(monkeypatch):
    height = 120
    width = 120
    center = Point2D(width // 2, height // 2)
    yy, xx = np.indices((height, width))
    distance = np.hypot(xx - center.x, yy - center.y)
    mask = np.where(distance <= 52, 255, 0).astype(np.uint8)
    npy_data = np.full((height, width), 2000, dtype=np.int32)
    npy_data[(distance > 25) & (distance <= 52) & (xx > center.x + 8)] = 2180

    data_integration = SimpleNamespace(
        coilId=1001,
        surface="S",
        key="S",
        npy_data=npy_data,
        npy_mask=mask,
        alarmData=FakeAlarmData(center),
        median_3d_mm=2000.0,
        currentSecondaryCoil=SimpleNamespace(Thickness=0),
        scan3dCoordinateScaleX=1.0,
        scan3dCoordinateScaleY=1.0,
        next_code="2",
        z_to_mm=lambda z: float(z),
        x_to_mm=lambda value: float(value),
    )

    captured = []
    monkeypatch.setattr(taper_processing.Globs.control, "taper_shape_type", DetectionTaperShapeType.LINE_TYPE)
    monkeypatch.setattr(taper_grading, "add_obj", captured.append)
    monkeypatch.setattr(
        taper_grading.alarmConfigProperty,
        "get_taper_shape_config",
        lambda di: TaperShapeConfig({
            "Base": {"name": "base", "height": [60, 80], "inner": 0, "outer": 0, "info": "base"},
        }, di),
    )

    taper_processing._detection_taper_shape_all_([data_integration])
    result = taper_grading.grading_alarm_taper_shape(data_integration)

    assert data_integration.alarmData.taper_shape_disabled is False
    assert len(data_integration.alarmData.lineDataDict) > 0
    assert result.grad == 3
    assert captured
    assert captured[0].out_taper_max_value >= 80.0


def test_find_line_max_min_filters_single_point_spike():
    line = np.array([[i, 0, 1000] for i in range(120)], dtype=float)
    line[119, 2] = 50000

    max_point, min_point = find_line_max_min(line, 10, use_iqr=True, type_="outer")

    assert max_point.z == 1000.0
    assert min_point.z == 1000.0


def test_find_line_max_min_filters_many_isolated_spikes_beyond_top_window():
    line = np.array([[i, 0, 1000] for i in range(1200)], dtype=float)
    line[1:203:2, 2] = 50000

    max_point, min_point = find_line_max_min(line, 10, use_iqr=True, type_="outer")

    assert max_point.z == 1000.0
    assert min_point.z == 1000.0

    low_line = np.array([[i, 0, 1000] for i in range(1200)], dtype=float)
    low_line[1:203:2, 2] = 20

    max_point, min_point = find_line_max_min(low_line, 10, use_iqr=True, type_="outer")

    assert max_point.z == 1000.0
    assert min_point.z == 1000.0


def test_find_line_max_min_keeps_clustered_taper_extremes():
    high_line = np.array([[i, 0, 1000] for i in range(120)], dtype=float)
    high_line[60, 2] = 50000
    high_line[61, 2] = 49000

    max_point, min_point = find_line_max_min(high_line, 10, use_iqr=True, type_="outer")

    assert max_point.x == 60
    assert max_point.z == 50000.0
    assert min_point.z == 1000.0

    low_line = np.array([[i, 0, 1000] for i in range(120)], dtype=float)
    low_line[60, 2] = 20
    low_line[61, 2] = 25

    max_point, min_point = find_line_max_min(low_line, 10, use_iqr=True, type_="outer")

    assert max_point.z == 1000.0
    assert min_point.x == 60
    assert min_point.z == 20.0


def test_valid_line_height_mask_rejects_non_finite_coordinates():
    line = np.array([
        [0, 0, 100],
        [np.nan, 1, 100],
        [2, np.inf, 100],
        [3, 0, np.nan],
        [4, 0, 0],
    ], dtype=float)

    assert valid_line_height_mask(line, 10).tolist() == [True, False, False, False, False]


def test_valid_line_height_mask_rejects_malformed_line_arrays():
    assert valid_line_height_mask([], 10).tolist() == []
    assert valid_line_height_mask(np.array([0, 0, 100]), 10).tolist() == [False, False, False]
    assert valid_line_height_mask(np.array([[0, 100], [1, 120]]), 10).tolist() == [False, False]

    max_point, min_point = find_line_max_min(np.array([[0, 100], [1, 120]]), 10, use_iqr=True)

    assert max_point is None
    assert min_point is None


def test_taper_shape_ray_points_cover_cardinal_angles():
    npy_data = (np.arange(121).reshape(11, 11) + 1000).astype(np.int32)
    mask = np.ones((11, 11), dtype=np.uint8) * 255
    center = Point2D(5, 5)
    targets = {
        0: Point2D(105, 5),
        90: Point2D(5, 105),
        180: Point2D(-95, 5),
        270: Point2D(5, -95),
    }

    for angle, target in targets.items():
        line_data = LineData(npy_data, mask, center, target)
        points = line_data.all_image_line_points(mask=True, ray=True)
        direction = np.array([target.x - center.x, target.y - center.y], dtype=float)
        vectors = points[:, :2].astype(float) - np.array([center.x, center.y], dtype=float)
        dots = vectors @ direction

        assert len(points) > 0, f"{angle} degree ray has no points"
        assert np.all(dots > 0), f"{angle} degree ray includes points behind the center"


def test_taper_shape_ray_points_deduplicate_corner_intersections_on_rectangular_image():
    npy_data = (np.arange(160).reshape(20, 8) + 1000).astype(np.int32)
    mask = np.ones((20, 8), dtype=np.uint8) * 255
    center = Point2D(5, 5)
    target = Point2D(15, 15)

    line_data = LineData(npy_data, mask, center, target)
    points = line_data.all_image_line_points(mask=True, ray=True)
    direction = np.array([target.x - center.x, target.y - center.y], dtype=float)
    vectors = points[:, :2].astype(float) - np.array([center.x, center.y], dtype=float)
    dots = vectors @ direction

    assert len(points) > 0
    assert np.all(dots > 0)


def test_line_data_points_cache_can_be_read_repeatedly():
    line_data = LineData(
        npy_data=np.ones((5, 5), dtype=np.int32) * 100,
        mask_image=np.ones((5, 5), dtype=np.uint8) * 255,
        p1=Point2D(2, 2),
        p2=Point2D(4, 2),
    )

    first_points = line_data.points
    second_points = line_data.points

    assert second_points is first_points
    assert len(second_points) > 0


def test_taper_shape_rotation_rejects_non_finite_center():
    data_integration = SimpleNamespace(
        alarmData=SimpleNamespace(
            flatRollData=SimpleNamespace(get_center=lambda: Point2D(np.inf, 5))
        ),
        npy_data=np.zeros((11, 11), dtype=np.int32),
        npy_mask=np.ones((11, 11), dtype=np.uint8) * 255,
    )

    with pytest.raises(ValueError, match="中心点坐标非有限"):
        taper_line.detection_taper_shape_by_rotation_angle(data_integration, 0)


def test_taper_shape_rotation_rejects_center_outside_image_bounds():
    data_integration = SimpleNamespace(
        alarmData=SimpleNamespace(
            flatRollData=SimpleNamespace(get_center=lambda: Point2D(12, 5))
        ),
        npy_data=np.zeros((11, 11), dtype=np.int32),
        npy_mask=np.ones((11, 11), dtype=np.uint8) * 255,
    )

    with pytest.raises(ValueError, match="center out of image bounds"):
        taper_line.detection_taper_shape_by_rotation_angle(data_integration, 0)


def test_taper_shape_rotation_rejects_mismatched_image_shapes():
    data_integration = SimpleNamespace(
        alarmData=SimpleNamespace(
            flatRollData=SimpleNamespace(get_center=lambda: Point2D(5, 5))
        ),
        npy_data=np.zeros((11, 11), dtype=np.int32),
        npy_mask=np.ones((10, 11), dtype=np.uint8) * 255,
    )

    with pytest.raises(ValueError, match="3D/mask shape mismatch"):
        taper_line.detection_taper_shape_by_rotation_angle(data_integration, 0)


def test_taper_shape_rotation_rejects_non_numeric_3d_image():
    data_integration = SimpleNamespace(
        alarmData=SimpleNamespace(
            flatRollData=SimpleNamespace(get_center=lambda: Point2D(5, 5))
        ),
        npy_data=np.full((11, 11), "bad-depth", dtype=object),
        npy_mask=np.ones((11, 11), dtype=np.uint8) * 255,
    )

    with pytest.raises(ValueError, match="3D image must be real numeric"):
        taper_line.detection_taper_shape_by_rotation_angle(data_integration, 0)


def test_taper_shape_rotation_accepts_bool_mask(monkeypatch):
    captured_mask_dtype = []

    class FakeLineData:
        def set_data_integration(self, data_integration):
            self.data_integration = data_integration

        def det_taper_shape(self):
            pass

        def set_rotation_angle(self, angle):
            self.rotation_angle = angle

    def fake_get_length_data_by_rotate(npy_data, mask, center, rotation_angle, ray=True):
        captured_mask_dtype.append(mask.dtype)
        return FakeLineData()

    monkeypatch.setattr(taper_line, "getLengthDataByRotate", fake_get_length_data_by_rotate)
    data_integration = SimpleNamespace(
        alarmData=SimpleNamespace(
            flatRollData=SimpleNamespace(get_center=lambda: Point2D(5, 5))
        ),
        npy_data=np.ones((11, 11), dtype=np.float32) * 100,
        npy_mask=np.ones((11, 11), dtype=bool),
    )

    taper_line.detection_taper_shape_by_rotation_angle(data_integration, 0)

    assert captured_mask_dtype == [np.dtype("bool")]


def test_taper_shape_rotation_accepts_center_object_with_xy_attrs():
    data_integration = SimpleNamespace(
        alarmData=SimpleNamespace(
            flatRollData=SimpleNamespace(
                get_center=lambda: SimpleNamespace(x=5.0, y=5.0)
            )
        ),
        npy_data=np.ones((11, 11), dtype=np.int32) * 100,
        npy_mask=np.ones((11, 11), dtype=np.uint8) * 255,
    )

    line_data = taper_line.detection_taper_shape_by_rotation_angle(data_integration, 0)

    assert line_data.rotation_angle == 0
    assert line_data.inner_max_point is not None
    assert line_data.outer_max_point is not None


def test_taper_shape_rotation_accepts_center_mapping():
    data_integration = SimpleNamespace(
        alarmData=SimpleNamespace(
            flatRollData=SimpleNamespace(get_center=lambda: {"x": "5.0", "y": 5})
        ),
        npy_data=np.ones((11, 11), dtype=np.int32) * 100,
        npy_mask=np.ones((11, 11), dtype=np.uint8) * 255,
    )

    line_data = taper_line.detection_taper_shape_by_rotation_angle(data_integration, 0)

    assert line_data.rotation_angle == 0
    assert line_data.inner_max_point is not None
    assert line_data.outer_max_point is not None


def test_taper_shape_rotation_accepts_center_mapping_aliases():
    data_integration = SimpleNamespace(
        alarmData=SimpleNamespace(
            flatRollData=SimpleNamespace(
                get_center=lambda: {"center_x": "5.0", "center_y": 5}
            )
        ),
        npy_data=np.ones((11, 11), dtype=np.int32) * 100,
        npy_mask=np.ones((11, 11), dtype=np.uint8) * 255,
    )

    line_data = taper_line.detection_taper_shape_by_rotation_angle(data_integration, 0)

    assert line_data.rotation_angle == 0
    assert line_data.inner_max_point is not None
    assert line_data.outer_max_point is not None


def test_taper_shape_rotation_rounds_float_center_to_nearest_pixel(monkeypatch):
    captured_centers = []

    class FakeLineData:
        def set_data_integration(self, data_integration):
            self.data_integration = data_integration

        def det_taper_shape(self):
            pass

        def set_rotation_angle(self, angle):
            self.rotation_angle = angle

    def fake_get_length_data_by_rotate(npy_data, mask, center, rotation_angle, ray=True):
        captured_centers.append((center.x, center.y))
        return FakeLineData()

    monkeypatch.setattr(taper_line, "getLengthDataByRotate", fake_get_length_data_by_rotate)
    data_integration = SimpleNamespace(
        alarmData=SimpleNamespace(
            flatRollData=SimpleNamespace(get_center=lambda: Point2D(5.7, 4.2))
        ),
        npy_data=np.ones((11, 11), dtype=np.int32) * 100,
        npy_mask=np.ones((11, 11), dtype=np.uint8) * 255,
    )

    taper_line.detection_taper_shape_by_rotation_angle(data_integration, 0)

    assert captured_centers == [(6, 4)]


def test_taper_shape_rotation_clamps_rounded_center_to_image_bounds(monkeypatch):
    captured_centers = []

    class FakeLineData:
        def set_data_integration(self, data_integration):
            self.data_integration = data_integration

        def det_taper_shape(self):
            pass

        def set_rotation_angle(self, angle):
            self.rotation_angle = angle

    def fake_get_length_data_by_rotate(npy_data, mask, center, rotation_angle, ray=True):
        captured_centers.append((center.x, center.y))
        return FakeLineData()

    monkeypatch.setattr(taper_line, "getLengthDataByRotate", fake_get_length_data_by_rotate)
    data_integration = SimpleNamespace(
        alarmData=SimpleNamespace(
            flatRollData=SimpleNamespace(get_center=lambda: Point2D(10.8, 10.6))
        ),
        npy_data=np.ones((11, 11), dtype=np.int32) * 100,
        npy_mask=np.ones((11, 11), dtype=np.uint8) * 255,
    )

    taper_line.detection_taper_shape_by_rotation_angle(data_integration, 0)

    assert captured_centers == [(10, 10)]


def test_line_data_ray_line_ignores_low_value_edge_noise():
    line_data = LineData(
        npy_data=np.zeros((1, 10), dtype=np.int32),
        mask_image=np.ones((1, 10), dtype=np.uint8) * 255,
        p1=Point2D(0, 0),
        p2=Point2D(9, 0),
    )
    line_data._ray_data_ = np.array([
        [0, 0, 5],
        [1, 0, 8],
        [2, 0, 100],
        [3, 0, 100],
        [4, 0, 100],
        [5, 0, 100],
        [6, 0, 100],
        [7, 0, 100],
        [8, 0, 9],
        [9, 0, 5],
    ], dtype=np.int32)

    ray_line = line_data.ray_line

    assert ray_line[0, 0] == 2
    assert ray_line[-1, 0] == 7


def test_line_data_ray_data_preserves_float_depth_values():
    line_data = LineData(
        npy_data=np.array([[0.0, 100.75, 101.25, 102.5, 103.0]], dtype=np.float32),
        mask_image=np.ones((1, 5), dtype=np.uint8) * 255,
        p1=Point2D(0, 0),
        p2=Point2D(4, 0),
    )

    ray_data = line_data.ray_data

    assert ray_data[0, 2] == pytest.approx(100.75)
    assert ray_data[1, 2] == pytest.approx(101.25)


def test_grading_alarm_taper_shape_records_min_points_and_worst_angle(monkeypatch):
    line_outer = SimpleNamespace(
        rotation_angle=40,
        outer_max_point=_point(10, 20, 260),
        outer_min_point=_point(11, 21, 100),
        inner_max_point=_point(12, 22, 180),
        inner_min_point=_point(13, 23, 90),
    )
    line_inner = SimpleNamespace(
        rotation_angle=130,
        outer_max_point=_point(30, 40, 150),
        outer_min_point=_point(31, 41, 95),
        inner_max_point=_point(32, 42, 250),
        inner_min_point=_point(33, 43, 80),
    )
    data_integration = FakeDataIntegration()
    data_integration.alarmData = SimpleNamespace(lineDataDict={40: line_outer, 130: line_inner})

    captured = []
    monkeypatch.setattr(taper_grading, "add_obj", captured.append)
    monkeypatch.setattr(
        taper_grading.alarmConfigProperty,
        "get_taper_shape_config",
        lambda di: TaperShapeConfig({
            "Base": {"name": "base", "height": [60, 80], "inner": 0, "outer": 0, "info": "base"},
        }, di),
    )

    result = taper_grading.grading_alarm_taper_shape(data_integration)

    assert result.grad == 3
    assert captured
    alarm = captured[0]
    assert alarm.out_taper_min_x == 31
    assert alarm.out_taper_min_value == -2.5
    assert alarm.in_taper_min_x == 33
    assert alarm.in_taper_min_value == -10.0
    assert alarm.rotation_angle == 40
    assert alarm.out_taper_max_value == 80.0
    assert alarm.in_taper_max_value == 75.0
    metadata = json.loads(alarm.data)
    assert metadata["worst_point_type"] == "outer_max_point"
    assert metadata["worst_x"] == 10.0
    assert metadata["worst_y"] == 20.0
    assert metadata["worst_z"] == 260.0
    assert metadata["worst_angle"] == 40.0
    assert metadata["worst_used_point_count"] == 0


def test_grading_alarm_taper_shape_accepts_key_without_surface(monkeypatch):
    line_positive = SimpleNamespace(
        rotation_angle=40,
        outer_max_point=_point(10, 20, 260),
        outer_min_point=_point(11, 21, 100),
        inner_max_point=_point(12, 22, 100),
        inner_min_point=_point(13, 23, 100),
    )
    data_integration = SimpleNamespace(
        coilId=1001,
        key="L",
        next_code="2",
        currentSecondaryCoil=SimpleNamespace(Thickness=0),
        median_3d_mm=50.0,
        scan3dCoordinateScaleX=1.0,
        scan3dCoordinateScaleY=1.0,
        alarmData=SimpleNamespace(lineDataDict={40: line_positive}),
        z_to_mm=lambda z: 10.0 + 0.5 * float(z),
        x_to_mm=lambda value: float(value),
    )

    captured = []
    monkeypatch.setattr(taper_grading, "add_obj", captured.append)
    monkeypatch.setattr(
        taper_grading.alarmConfigProperty,
        "get_taper_shape_config",
        lambda di: TaperShapeConfig({
            "Base": {"name": "base", "height": [60, 80], "inner": 0, "outer": 0, "info": "base"},
        }, di),
    )

    result = taper_grading.grading_alarm_taper_shape(data_integration)

    assert result.grad == 3
    assert captured[0].surface == "L"


def test_grading_alarm_taper_shape_preserves_result_when_detail_save_fails(monkeypatch):
    line_positive = SimpleNamespace(
        rotation_angle=40,
        outer_max_point=_point(10, 20, 260),
        outer_min_point=_point(11, 21, 100),
        inner_max_point=_point(12, 22, 100),
        inner_min_point=_point(13, 23, 100),
    )
    data_integration = FakeDataIntegration()
    data_integration.alarmData = SimpleNamespace(lineDataDict={40: line_positive})

    warnings = []

    def fail_save(_alarm_taper_shape):
        raise RuntimeError("db unavailable")

    monkeypatch.setattr(taper_grading, "add_obj", fail_save)
    monkeypatch.setattr(taper_grading.logger, "warning", warnings.append)
    monkeypatch.setattr(
        taper_grading.alarmConfigProperty,
        "get_taper_shape_config",
        lambda di: TaperShapeConfig({
            "Base": {"name": "base", "height": [60, 80], "inner": 0, "outer": 0, "info": "base"},
        }, di),
    )

    result = taper_grading.grading_alarm_taper_shape(data_integration)

    assert result.grad == 3
    assert "80.00 >= 80.00" in result.errorMsg
    assert "db unavailable" in result.errorMsg
    assert warnings
    assert "db unavailable" in warnings[0]


def test_grading_alarm_taper_shape_skips_non_finite_cached_metrics(monkeypatch):
    invalid_line = SimpleNamespace(
        rotation_angle=20,
        outer_max_point=_point(10, 20, np.inf),
        outer_min_point=_point(11, 21, 100),
        inner_max_point=_point(12, 22, 100),
        inner_min_point=_point(13, 23, 100),
    )
    valid_line = SimpleNamespace(
        rotation_angle=40,
        outer_max_point=_point(30, 40, 260),
        outer_min_point=_point(31, 41, 100),
        inner_max_point=_point(32, 42, 100),
        inner_min_point=_point(33, 43, 100),
    )
    data_integration = FakeDataIntegration()
    data_integration.alarmData = SimpleNamespace(lineDataDict={20: invalid_line, 40: valid_line})

    captured = []
    monkeypatch.setattr(taper_grading, "add_obj", captured.append)
    monkeypatch.setattr(
        taper_grading.alarmConfigProperty,
        "get_taper_shape_config",
        lambda di: TaperShapeConfig({
            "Base": {"name": "base", "height": [60, 80], "inner": 0, "outer": 0, "info": "base"},
        }, di),
    )

    result = taper_grading.grading_alarm_taper_shape(data_integration)

    assert result.grad == 3
    assert captured
    assert captured[0].rotation_angle == 40
    assert captured[0].out_taper_max_value == 80.0
    assert json.loads(captured[0].data)["valid_line_count"] == 1


def test_grading_alarm_taper_shape_grades_negative_deviation(monkeypatch):
    line_negative = SimpleNamespace(
        rotation_angle=220,
        outer_max_point=_point(10, 20, 100),
        outer_min_point=_point(11, 21, 10),
        inner_max_point=_point(12, 22, 100),
        inner_min_point=_point(13, 23, 95),
    )
    data_integration = FakeDataIntegration()
    data_integration.median_3d_mm = 100.0
    data_integration.z_to_mm = lambda z: float(z)
    data_integration.alarmData = SimpleNamespace(lineDataDict={220: line_negative})

    captured = []
    monkeypatch.setattr(taper_grading, "add_obj", captured.append)
    monkeypatch.setattr(
        taper_grading.alarmConfigProperty,
        "get_taper_shape_config",
        lambda di: TaperShapeConfig({
            "Base": {"name": "base", "height": [60, 80], "inner": 0, "outer": 0, "info": "base"},
        }, di),
    )

    result = taper_grading.grading_alarm_taper_shape(data_integration)

    assert result.grad == 3
    assert "外塔最低值-90.00 <= -80.00" in result.errorMsg
    assert captured[0].rotation_angle == 220
    assert captured[0].out_taper_min_value == -90.0
    metadata = json.loads(captured[0].data)
    assert metadata["worst_point_type"] == "outer_min_point"
    assert metadata["worst_x"] == 11.0
    assert metadata["worst_y"] == 21.0
    assert metadata["worst_z"] == 10.0
    assert metadata["worst_angle"] == 220.0


def test_grading_alarm_taper_shape_ignores_zero_and_normalizes_negative_limits(monkeypatch):
    line_positive = SimpleNamespace(
        rotation_angle=20,
        outer_max_point=_point(10, 20, 140),
        outer_min_point=_point(11, 21, 100),
        inner_max_point=_point(12, 22, 100),
        inner_min_point=_point(13, 23, 100),
    )
    data_integration = FakeDataIntegration()
    data_integration.alarmData = SimpleNamespace(lineDataDict={20: line_positive})

    captured = []
    monkeypatch.setattr(taper_grading, "add_obj", captured.append)
    monkeypatch.setattr(
        taper_grading.alarmConfigProperty,
        "get_taper_shape_config",
        lambda di: TaperShapeConfig({
            "Base": {"name": "base", "height": [0, -60], "inner": 0, "outer": 0, "info": "base"},
        }, di),
    )

    result = taper_grading.grading_alarm_taper_shape(data_integration)

    assert result.grad == 1
    assert result.errorMsg == "正常"
    assert json.loads(captured[0].data)["height_limits"] == [60.0]


def test_grading_alarm_taper_shape_uses_default_limits_when_config_limits_empty(monkeypatch):
    line_positive = SimpleNamespace(
        rotation_angle=20,
        outer_max_point=_point(10, 20, 260),
        outer_min_point=_point(11, 21, 100),
        inner_max_point=_point(12, 22, 100),
        inner_min_point=_point(13, 23, 100),
    )
    data_integration = FakeDataIntegration()
    data_integration.alarmData = SimpleNamespace(lineDataDict={20: line_positive})

    captured = []
    monkeypatch.setattr(taper_grading, "add_obj", captured.append)
    monkeypatch.setattr(
        taper_grading.alarmConfigProperty,
        "get_taper_shape_config",
        lambda di: TaperShapeConfig({
            "Base": {"name": "base", "height": [], "inner": 0, "outer": 0, "info": "base"},
        }, di),
    )

    result = taper_grading.grading_alarm_taper_shape(data_integration)

    assert result.grad == 3
    assert captured
    assert captured[0].out_taper_max_value == 80.0
    assert json.loads(captured[0].data)["height_limits"] == [60.0, 80.0]


def test_grading_alarm_taper_shape_uses_default_limits_when_config_limits_non_finite(monkeypatch):
    line_positive = SimpleNamespace(
        rotation_angle=20,
        outer_max_point=_point(10, 20, 260),
        outer_min_point=_point(11, 21, 100),
        inner_max_point=_point(12, 22, 100),
        inner_min_point=_point(13, 23, 100),
    )
    data_integration = FakeDataIntegration()
    data_integration.alarmData = SimpleNamespace(lineDataDict={20: line_positive})

    captured = []
    monkeypatch.setattr(taper_grading, "add_obj", captured.append)
    monkeypatch.setattr(
        taper_grading.alarmConfigProperty,
        "get_taper_shape_config",
        lambda di: TaperShapeConfig({
            "Base": {"name": "base", "height": [np.inf, "nan"], "inner": 0, "outer": 0, "info": "base"},
        }, di),
    )

    result = taper_grading.grading_alarm_taper_shape(data_integration)

    assert result.grad == 3
    assert captured
    assert captured[0].out_taper_max_value == 80.0
    assert json.loads(captured[0].data)["height_limits"] == [60.0, 80.0]


def test_grading_alarm_taper_shape_parses_string_height_limits(monkeypatch):
    line_positive = SimpleNamespace(
        rotation_angle=20,
        outer_max_point=_point(10, 20, 210),
        outer_min_point=_point(11, 21, 100),
        inner_max_point=_point(12, 22, 100),
        inner_min_point=_point(13, 23, 100),
    )
    data_integration = FakeDataIntegration()
    data_integration.alarmData = SimpleNamespace(lineDataDict={20: line_positive})

    captured = []
    monkeypatch.setattr(taper_grading, "add_obj", captured.append)
    monkeypatch.setattr(
        taper_grading.alarmConfigProperty,
        "get_taper_shape_config",
        lambda di: TaperShapeConfig({
            "Base": {"name": "base", "height": "50，80", "inner": 0, "outer": 0, "info": "base"},
        }, di),
    )

    result = taper_grading.grading_alarm_taper_shape(data_integration)

    assert result.grad == 2
    assert "外塔最高值55.00 >= 50.00" in result.errorMsg
    assert json.loads(captured[0].data)["height_limits"] == [50.0, 80.0]


@pytest.mark.parametrize(
    ("height_limits", "expected"),
    [
        ("50、80", [50.0, 80.0]),
        ("50mm/80mm", [50.0, 80.0]),
        ("±60 mm", [60.0]),
        ("height: 45 ; 90", [45.0, 90.0]),
    ],
)
def test_taper_shape_height_limits_parse_common_text_formats(height_limits, expected):
    assert normalize_taper_height_limits(height_limits) == expected
    threshold = min(expected)
    assert taper_error_threshold_from_limits(height_limits) == (threshold, threshold)


def test_grading_alarm_taper_shape_ignores_configured_outer_ring(monkeypatch):
    ray_line = np.array([[i, 0, 100] for i in range(10)], dtype=float)
    ray_line[-1, 2] = 260
    line_data = SimpleNamespace(
        rotation_angle=0,
        ray_line=ray_line,
        outer_max_point=_point(9, 0, 260),
        outer_min_point=_point(5, 0, 100),
        inner_max_point=_point(0, 0, 100),
        inner_min_point=_point(0, 0, 100),
    )
    data_integration = FakeDataIntegration()
    data_integration.currentSecondaryCoil = SimpleNamespace(Thickness=1)
    data_integration.alarmData = SimpleNamespace(lineDataDict={0: line_data})

    captured = []
    monkeypatch.setattr(taper_grading, "add_obj", captured.append)
    monkeypatch.setattr(
        taper_grading.alarmConfigProperty,
        "get_taper_shape_config",
        lambda di: TaperShapeConfig({
            "Base": {"name": "base", "height": [60, 80], "inner": 0, "outer": 1, "info": "base"},
        }, di),
    )

    result = taper_grading.grading_alarm_taper_shape(data_integration)

    assert result.grad == 1
    assert captured
    assert captured[0].out_taper_max_value == 0.0
    metadata = json.loads(captured[0].data)
    assert metadata["ignored_outer_mm"] == 1.0
    assert metadata["applied_ignored_outer_mm"] == 1.0
    assert metadata["outer_skip_count"] == 1


def test_grading_alarm_taper_shape_uses_y_scale_for_vertical_ignore_distance(monkeypatch):
    ray_line = np.array([[0, i, 100] for i in range(10)], dtype=float)
    ray_line[-2, 2] = 260
    line_data = SimpleNamespace(
        rotation_angle=90,
        ray_line=ray_line,
        outer_max_point=_point(0, 8, 260),
        outer_min_point=_point(0, 5, 100),
        inner_max_point=_point(0, 0, 100),
        inner_min_point=_point(0, 0, 100),
    )
    data_integration = FakeDataIntegration()
    data_integration.scan3dCoordinateScaleX = 0.5
    data_integration.scan3dCoordinateScaleY = 2.0
    data_integration.currentSecondaryCoil = SimpleNamespace(Thickness=2)
    data_integration.alarmData = SimpleNamespace(lineDataDict={90: line_data})

    captured = []
    monkeypatch.setattr(taper_grading, "add_obj", captured.append)
    monkeypatch.setattr(
        taper_grading.alarmConfigProperty,
        "get_taper_shape_config",
        lambda di: TaperShapeConfig({
            "Base": {"name": "base", "height": [60, 80], "inner": 0, "outer": 1, "info": "base"},
        }, di),
    )

    result = taper_grading.grading_alarm_taper_shape(data_integration)

    assert result.grad == 3
    assert captured[0].out_taper_max_value == 80.0
    assert captured[0].rotation_angle == 90


def test_grading_alarm_taper_shape_keeps_original_inner_outer_boundary_after_trim(monkeypatch):
    ray_line = np.array([[i, 0, 100] for i in range(10)], dtype=float)
    ray_line[5, 2] = 260
    line_data = SimpleNamespace(
        rotation_angle=0,
        ray_line=ray_line,
        outer_max_point=_point(5, 0, 260),
        outer_min_point=_point(6, 0, 100),
        inner_max_point=_point(4, 0, 100),
        inner_min_point=_point(0, 0, 100),
    )
    data_integration = FakeDataIntegration()
    data_integration.currentSecondaryCoil = SimpleNamespace(Thickness=1)
    data_integration.alarmData = SimpleNamespace(lineDataDict={0: line_data})

    captured = []
    monkeypatch.setattr(taper_grading, "add_obj", captured.append)
    monkeypatch.setattr(
        taper_grading.alarmConfigProperty,
        "get_taper_shape_config",
        lambda di: TaperShapeConfig({
            "Base": {"name": "base", "height": [60, 80], "inner": 2, "outer": 0, "info": "base"},
        }, di),
    )

    result = taper_grading.grading_alarm_taper_shape(data_integration)

    assert result.grad == 3
    assert captured[0].out_taper_max_value == 80.0
    assert captured[0].in_taper_max_value == 0.0


def test_grading_alarm_taper_shape_keeps_boundary_with_inner_mask_holes(monkeypatch):
    ray_line = np.array([[i, 0, 100] for i in range(10)], dtype=float)
    ray_line[1:4, 2] = 0
    ray_line[5, 2] = 260
    line_data = SimpleNamespace(
        rotation_angle=0,
        ray_line=ray_line,
        outer_max_point=_point(5, 0, 260),
        outer_min_point=_point(6, 0, 100),
        inner_max_point=_point(4, 0, 100),
        inner_min_point=_point(4, 0, 100),
    )
    data_integration = FakeDataIntegration()
    data_integration.alarmData = SimpleNamespace(lineDataDict={0: line_data})

    captured = []
    monkeypatch.setattr(taper_grading, "add_obj", captured.append)
    monkeypatch.setattr(
        taper_grading.alarmConfigProperty,
        "get_taper_shape_config",
        lambda di: TaperShapeConfig({
            "Base": {"name": "base", "height": [60, 80], "inner": 0, "outer": 0, "info": "base"},
        }, di),
    )

    result = taper_grading.grading_alarm_taper_shape(data_integration)

    assert result.grad == 3
    assert captured[0].out_taper_max_value == 80.0
    assert captured[0].in_taper_max_value == 0.0


def test_grading_alarm_taper_shape_recomputes_metrics_from_ray_line(monkeypatch):
    ray_line = np.array([[i, 0, 100] for i in range(10)], dtype=float)
    ray_line[6, 2] = 260
    line_data = SimpleNamespace(
        rotation_angle=0,
        ray_line=ray_line,
    )
    data_integration = FakeDataIntegration()
    data_integration.alarmData = SimpleNamespace(lineDataDict={0: line_data})

    captured = []
    monkeypatch.setattr(taper_grading, "add_obj", captured.append)
    monkeypatch.setattr(
        taper_grading.alarmConfigProperty,
        "get_taper_shape_config",
        lambda di: TaperShapeConfig({
            "Base": {"name": "base", "height": [60, 80], "inner": 0, "outer": 0, "info": "base"},
        }, di),
    )

    result = taper_grading.grading_alarm_taper_shape(data_integration)

    assert result.grad == 3
    assert captured
    assert captured[0].out_taper_max_x == 6
    assert captured[0].out_taper_max_value == 80.0
    assert json.loads(captured[0].data)["valid_line_count"] == 1


def test_grading_alarm_taper_shape_skips_malformed_ray_line(monkeypatch):
    malformed_line = SimpleNamespace(
        rotation_angle=10,
        ray_line=np.array([0, 0, 260], dtype=float),
    )
    ray_line = np.array([[i, 0, 100] for i in range(10)], dtype=float)
    ray_line[6, 2] = 260
    valid_line = SimpleNamespace(
        rotation_angle=40,
        ray_line=ray_line,
    )
    data_integration = FakeDataIntegration()
    data_integration.alarmData = SimpleNamespace(lineDataDict={10: malformed_line, 40: valid_line})

    captured = []
    monkeypatch.setattr(taper_grading, "add_obj", captured.append)
    monkeypatch.setattr(
        taper_grading.alarmConfigProperty,
        "get_taper_shape_config",
        lambda di: TaperShapeConfig({
            "Base": {"name": "base", "height": [60, 80], "inner": 0, "outer": 0, "info": "base"},
        }, di),
    )

    result = taper_grading.grading_alarm_taper_shape(data_integration)

    assert result.grad == 3
    assert captured
    assert captured[0].rotation_angle == 40
    assert captured[0].out_taper_max_value == 80.0
    assert json.loads(captured[0].data)["valid_line_count"] == 1


def test_grading_alarm_taper_shape_rejects_sparse_side_points(monkeypatch):
    sparse_line = SimpleNamespace(
        rotation_angle=0,
        ray_line=np.array([
            [0, 0, 100],
            [1, 0, 0],
            [2, 0, 0],
            [3, 0, 260],
        ], dtype=float),
        outer_max_point=_point(3, 0, 260),
        outer_min_point=_point(3, 0, 260),
        inner_max_point=_point(0, 0, 100),
        inner_min_point=_point(0, 0, 100),
    )
    data_integration = FakeDataIntegration()
    data_integration.alarmData = SimpleNamespace(lineDataDict={0: sparse_line})

    captured = []
    monkeypatch.setattr(taper_grading, "add_obj", captured.append)
    monkeypatch.setattr(
        taper_grading.alarmConfigProperty,
        "get_taper_shape_config",
        lambda di: TaperShapeConfig({
            "Base": {"name": "base", "height": [60, 80], "inner": 0, "outer": 0, "info": "base"},
        }, di),
    )

    result = taper_grading.grading_alarm_taper_shape(data_integration)

    assert result.grad == 3
    assert captured == []
    assert "无有效线数据" in result.errorMsg
    assert "塔形线有效点不足 inner=1 outer=1 min=2" in result.errorMsg
    assert data_integration.alarmData.taper_shape_grading_errors == [
        "0度: 塔形线有效点不足 inner=1 outer=1 min=2"
    ]


def test_grading_alarm_taper_shape_rejects_low_coverage_line(monkeypatch):
    low_coverage_line = SimpleNamespace(
        rotation_angle=0,
        ray_line=np.array([
            [0, 0, 100],
            [1, 0, 100],
            [2, 0, 0],
            [3, 0, 0],
            [4, 0, 0],
            [5, 0, 0],
            [6, 0, 0],
            [7, 0, 0],
            [8, 0, 0],
            [9, 0, 0],
            [10, 0, 260],
            [11, 0, 100],
        ], dtype=float),
        outer_max_point=_point(10, 0, 260),
        outer_min_point=_point(11, 0, 100),
        inner_max_point=_point(0, 0, 100),
        inner_min_point=_point(1, 0, 100),
    )
    data_integration = FakeDataIntegration()
    data_integration.alarmData = SimpleNamespace(lineDataDict={0: low_coverage_line})

    captured = []
    monkeypatch.setattr(taper_grading, "add_obj", captured.append)
    monkeypatch.setattr(
        taper_grading.alarmConfigProperty,
        "get_taper_shape_config",
        lambda di: TaperShapeConfig({
            "Base": {"name": "base", "height": [60, 80], "inner": 0, "outer": 0, "info": "base"},
        }, di),
    )

    result = taper_grading.grading_alarm_taper_shape(data_integration)

    assert result.grad == 3
    assert captured == []
    assert "塔形线有效覆盖率不足 coverage=0.33 min=0.50" in result.errorMsg
    assert data_integration.alarmData.taper_shape_grading_errors == [
        "0度: 塔形线有效覆盖率不足 coverage=0.33 min=0.50"
    ]


def test_grading_alarm_taper_shape_rejects_low_side_coverage_line(monkeypatch):
    ray_line = np.array([[i, 0, 100] for i in range(12)], dtype=float)
    ray_line[1:5, 2] = 0
    ray_line[8, 2] = 260
    low_side_coverage_line = SimpleNamespace(
        rotation_angle=0,
        ray_line=ray_line,
        outer_max_point=_point(8, 0, 260),
        outer_min_point=_point(6, 0, 100),
        inner_max_point=_point(0, 0, 100),
        inner_min_point=_point(5, 0, 100),
    )
    data_integration = FakeDataIntegration()
    data_integration.alarmData = SimpleNamespace(lineDataDict={0: low_side_coverage_line})

    captured = []
    monkeypatch.setattr(taper_grading, "add_obj", captured.append)
    monkeypatch.setattr(
        taper_grading.alarmConfigProperty,
        "get_taper_shape_config",
        lambda di: TaperShapeConfig({
            "Base": {"name": "base", "height": [60, 80], "inner": 0, "outer": 0, "info": "base"},
        }, di),
    )

    result = taper_grading.grading_alarm_taper_shape(data_integration)

    assert result.grad == 3
    assert captured == []
    assert "塔形线单侧有效覆盖率不足 inner=0.33 outer=1.00 min=0.40" in result.errorMsg
    assert data_integration.alarmData.taper_shape_grading_errors == [
        "0度: 塔形线单侧有效覆盖率不足 inner=0.33 outer=1.00 min=0.40"
    ]


def test_grading_alarm_taper_shape_flags_low_angle_coverage(monkeypatch):
    valid_line = SimpleNamespace(
        rotation_angle=40,
        outer_max_point=_point(10, 20, 100),
        outer_min_point=_point(11, 21, 100),
        inner_max_point=_point(12, 22, 100),
        inner_min_point=_point(13, 23, 100),
    )
    data_integration = FakeDataIntegration()
    data_integration.alarmData = SimpleNamespace(
        lineDataDict={40: valid_line},
        taper_shape_attempt_count=36,
    )

    captured = []
    monkeypatch.setattr(taper_grading, "add_obj", captured.append)
    monkeypatch.setattr(
        taper_grading.alarmConfigProperty,
        "get_taper_shape_config",
        lambda di: TaperShapeConfig({
            "Base": {"name": "base", "height": [60, 80], "inner": 0, "outer": 0, "info": "base"},
        }, di),
    )

    result = taper_grading.grading_alarm_taper_shape(data_integration)

    assert result.grad == 3
    assert "塔形检测质量不足" in result.errorMsg
    assert "塔形有效角度覆盖不足" in result.errorMsg
    assert "valid=1 total=36 coverage=0.03 min=0.50" in result.errorMsg

    metadata = json.loads(captured[0].data)
    assert metadata["valid_line_count"] == 1
    assert metadata["taper_attempt_count"] == 36
    assert metadata["valid_angle_coverage_ratio"] == pytest.approx(1 / 36)
    assert metadata["valid_angle_coverage_min"] == 0.5


def test_grading_alarm_taper_shape_records_partial_error_metadata(monkeypatch):
    malformed_line = SimpleNamespace(
        rotation_angle=10,
        ray_line=np.array([0, 0, 260], dtype=float),
    )
    valid_line = SimpleNamespace(
        rotation_angle=40,
        outer_max_point=_point(10, 20, 260),
        outer_min_point=_point(11, 21, 100),
        inner_max_point=_point(12, 22, 100),
        inner_min_point=_point(13, 23, 100),
    )
    detection_errors = [
        "0度: center out of image bounds",
        "20度: 3D/mask shape mismatch",
        "30度: line data empty",
        "50度: line data empty",
    ]
    data_integration = FakeDataIntegration()
    data_integration.alarmData = SimpleNamespace(
        lineDataDict={10: malformed_line, 40: valid_line},
        taper_shape_errors=detection_errors,
    )

    captured = []
    monkeypatch.setattr(taper_grading, "add_obj", captured.append)
    monkeypatch.setattr(
        taper_grading.alarmConfigProperty,
        "get_taper_shape_config",
        lambda di: TaperShapeConfig({
            "Base": {"name": "base", "height": [60, 80], "inner": 0, "outer": 0, "info": "base"},
        }, di),
    )

    result = taper_grading.grading_alarm_taper_shape(data_integration)

    assert result.grad == 3
    assert "80.00 >= 80.00" in result.errorMsg
    assert "塔形检测部分角度失败" in result.errorMsg
    assert "另有1个角度失败" in result.errorMsg
    assert "塔形分级部分线无效" in result.errorMsg
    assert "10度: 无有效塔形线指标" in result.errorMsg

    metadata = json.loads(captured[0].data)
    assert metadata["valid_line_count"] == 1
    assert metadata["detection_error_count"] == 4
    assert metadata["detection_error_preview"] == detection_errors[:3]
    assert metadata["grading_error_count"] == 1
    assert metadata["grading_error_preview"] == ["10度: 无有效塔形线指标"]


def test_grading_alarm_taper_shape_treats_single_error_string_as_one_message(monkeypatch):
    valid_line = SimpleNamespace(
        rotation_angle=40,
        outer_max_point=_point(10, 20, 100),
        outer_min_point=_point(11, 21, 100),
        inner_max_point=_point(12, 22, 100),
        inner_min_point=_point(13, 23, 100),
    )
    detection_error = "0度: center out of image bounds"
    data_integration = FakeDataIntegration()
    data_integration.alarmData = SimpleNamespace(
        lineDataDict={40: valid_line},
        taper_shape_errors=detection_error,
    )

    captured = []
    monkeypatch.setattr(taper_grading, "add_obj", captured.append)
    monkeypatch.setattr(
        taper_grading.alarmConfigProperty,
        "get_taper_shape_config",
        lambda di: TaperShapeConfig({
            "Base": {"name": "base", "height": [60, 80], "inner": 0, "outer": 0, "info": "base"},
        }, di),
    )

    result = taper_grading.grading_alarm_taper_shape(data_integration)

    assert result.grad == 1
    assert "塔形检测部分角度失败：0度: center out of image bounds" in result.errorMsg
    assert "塔形有效角度覆盖不足" not in result.errorMsg

    metadata = json.loads(captured[0].data)
    assert metadata["valid_line_count"] == 1
    assert metadata["taper_attempt_count"] == 2
    assert metadata["detection_error_count"] == 1
    assert metadata["detection_error_preview"] == [detection_error]


def test_grading_alarm_taper_shape_uses_cached_metrics_when_ray_line_fails(monkeypatch):
    class CachedLineData:
        rotation_angle = 30
        outer_max_point = _point(10, 20, 260)
        outer_min_point = _point(11, 21, 100)
        inner_max_point = _point(12, 22, 100)
        inner_min_point = _point(13, 23, 100)

        @property
        def ray_line(self):
            raise ValueError("raw ray line unavailable")

    data_integration = FakeDataIntegration()
    data_integration.alarmData = SimpleNamespace(lineDataDict={30: CachedLineData()})

    captured = []
    monkeypatch.setattr(taper_grading, "add_obj", captured.append)
    monkeypatch.setattr(
        taper_grading.alarmConfigProperty,
        "get_taper_shape_config",
        lambda di: TaperShapeConfig({
            "Base": {"name": "base", "height": [60, 80], "inner": 0, "outer": 0, "info": "base"},
        }, di),
    )

    result = taper_grading.grading_alarm_taper_shape(data_integration)

    assert result.grad == 3
    assert captured
    assert captured[0].rotation_angle == 30
    assert captured[0].out_taper_max_value == 80.0
    assert json.loads(captured[0].data)["valid_line_count"] == 1


def test_grading_alarm_taper_shape_rejects_cached_metrics_when_trim_needs_raw_line(monkeypatch):
    class CachedLineData:
        rotation_angle = 30
        outer_max_point = _point(10, 20, 260)
        outer_min_point = _point(11, 21, 100)
        inner_max_point = _point(12, 22, 100)
        inner_min_point = _point(13, 23, 100)

        @property
        def ray_line(self):
            raise ValueError("raw ray line unavailable")

    data_integration = FakeDataIntegration()
    data_integration.currentSecondaryCoil = SimpleNamespace(Thickness=1)
    data_integration.alarmData = SimpleNamespace(lineDataDict={30: CachedLineData()})

    captured = []
    monkeypatch.setattr(taper_grading, "add_obj", captured.append)
    monkeypatch.setattr(
        taper_grading.alarmConfigProperty,
        "get_taper_shape_config",
        lambda di: TaperShapeConfig({
            "Base": {"name": "base", "height": [60, 80], "inner": 0, "outer": 1, "info": "base"},
        }, di),
    )

    result = taper_grading.grading_alarm_taper_shape(data_integration)

    assert result.grad == 3
    assert captured == []
    assert "无有效线数据" in result.errorMsg
    assert data_integration.alarmData.taper_shape_grading_errors == [
        "30度: 无有效塔形线指标"
    ]


def test_grading_alarm_taper_shape_does_not_use_cache_for_malformed_raw_line(monkeypatch):
    malformed_cached_line = SimpleNamespace(
        rotation_angle=30,
        ray_line=np.array([0, 0, 260], dtype=float),
        outer_max_point=_point(10, 20, 260),
        outer_min_point=_point(11, 21, 100),
        inner_max_point=_point(12, 22, 100),
        inner_min_point=_point(13, 23, 100),
    )
    data_integration = FakeDataIntegration()
    data_integration.alarmData = SimpleNamespace(lineDataDict={30: malformed_cached_line})

    captured = []
    monkeypatch.setattr(taper_grading, "add_obj", captured.append)
    monkeypatch.setattr(
        taper_grading.alarmConfigProperty,
        "get_taper_shape_config",
        lambda di: TaperShapeConfig({
            "Base": {"name": "base", "height": [60, 80], "inner": 0, "outer": 0, "info": "base"},
        }, di),
    )

    result = taper_grading.grading_alarm_taper_shape(data_integration)

    assert result.grad == 3
    assert captured == []
    assert "无有效线数据" in result.errorMsg
    assert data_integration.alarmData.taper_shape_grading_errors == [
        "30度: 无有效塔形线指标"
    ]


def test_grading_alarm_taper_shape_does_not_use_cache_after_trim_exhausts_side(monkeypatch):
    ray_line = np.array([[i, 0, 100] for i in range(10)], dtype=float)
    ray_line[-1, 2] = 260
    line_data = SimpleNamespace(
        rotation_angle=0,
        ray_line=ray_line,
        outer_max_point=_point(9, 0, 260),
        outer_min_point=_point(5, 0, 100),
        inner_max_point=_point(0, 0, 100),
        inner_min_point=_point(0, 0, 100),
    )
    data_integration = FakeDataIntegration()
    data_integration.currentSecondaryCoil = SimpleNamespace(Thickness=10)
    data_integration.alarmData = SimpleNamespace(lineDataDict={0: line_data})

    captured = []
    monkeypatch.setattr(taper_grading, "add_obj", captured.append)
    monkeypatch.setattr(
        taper_grading.alarmConfigProperty,
        "get_taper_shape_config",
        lambda di: TaperShapeConfig({
            "Base": {"name": "base", "height": [60, 80], "inner": 0, "outer": 1, "info": "base"},
        }, di),
    )

    result = taper_grading.grading_alarm_taper_shape(data_integration)

    assert result.grad == 3
    assert captured == []
    assert "塔形线配置忽略距离过大" in result.errorMsg
    assert data_integration.alarmData.taper_shape_grading_errors == [
        "0度: 塔形线配置忽略距离过大 inner_skip=0/5 outer_skip=5/5"
    ]


def test_grading_alarm_taper_shape_ignores_non_finite_coordinate_points(monkeypatch):
    ray_line = np.array([[i, 0, 100] for i in range(10)], dtype=float)
    ray_line[0, 0] = np.nan
    ray_line[6, 2] = 260
    line_data = SimpleNamespace(
        rotation_angle=0,
        ray_line=ray_line,
    )
    data_integration = FakeDataIntegration()
    data_integration.alarmData = SimpleNamespace(lineDataDict={0: line_data})

    captured = []
    monkeypatch.setattr(taper_grading, "add_obj", captured.append)
    monkeypatch.setattr(
        taper_grading.alarmConfigProperty,
        "get_taper_shape_config",
        lambda di: TaperShapeConfig({
            "Base": {"name": "base", "height": [60, 80], "inner": 0, "outer": 0, "info": "base"},
        }, di),
    )

    result = taper_grading.grading_alarm_taper_shape(data_integration)

    assert result.grad == 3
    assert captured
    assert captured[0].out_taper_max_value == 80.0
    assert json.loads(captured[0].data)["valid_line_count"] == 1


def test_grading_alarm_taper_shape_treats_non_finite_ignore_config_as_zero(monkeypatch):
    ray_line = np.array([[i, 0, 100] for i in range(10)], dtype=float)
    ray_line[6, 2] = 260
    line_data = SimpleNamespace(
        rotation_angle=np.inf,
        ray_line=ray_line,
    )
    data_integration = FakeDataIntegration()
    data_integration.currentSecondaryCoil = SimpleNamespace(Thickness=np.inf)
    data_integration.alarmData = SimpleNamespace(lineDataDict={0: line_data})

    captured = []
    monkeypatch.setattr(taper_grading, "add_obj", captured.append)
    monkeypatch.setattr(
        taper_grading.alarmConfigProperty,
        "get_taper_shape_config",
        lambda di: TaperShapeConfig({
            "Base": {"name": "base", "height": [60, 80], "inner": np.inf, "outer": np.inf, "info": "base"},
        }, di),
    )

    result = taper_grading.grading_alarm_taper_shape(data_integration)

    assert result.grad == 3
    assert captured[0].rotation_angle == 0.0
    assert captured[0].out_taper_max_value == 80.0
    assert "Infinity" not in captured[0].data
    assert "NaN" not in captured[0].data
    metadata = json.loads(captured[0].data)
    assert metadata["inner_ignore"] == 0.0
    assert metadata["outer_ignore"] == 0.0
    assert metadata["ignored_inner_mm"] == 0.0
    assert metadata["ignored_outer_mm"] == 0.0
    assert metadata["outer_angle"] == 0.0


def test_grading_alarm_taper_shape_treats_bad_distance_fallback_as_no_trim(monkeypatch):
    ray_line = np.array([[i, 0, 100] for i in range(10)], dtype=float)
    ray_line[-1, 2] = 260
    line_data = SimpleNamespace(
        rotation_angle=0,
        ray_line=ray_line,
    )
    data_integration = FakeDataIntegration()
    data_integration.scan3dCoordinateScaleX = None
    data_integration.scan3dCoordinateScaleY = None
    data_integration.x_to_mm = lambda value: (_ for _ in ()).throw(ValueError("bad scale"))
    data_integration.currentSecondaryCoil = SimpleNamespace(Thickness=2)
    data_integration.alarmData = SimpleNamespace(lineDataDict={0: line_data})

    captured = []
    monkeypatch.setattr(taper_grading, "add_obj", captured.append)
    monkeypatch.setattr(
        taper_grading.alarmConfigProperty,
        "get_taper_shape_config",
        lambda di: TaperShapeConfig({
            "Base": {"name": "base", "height": [60, 80], "inner": 0, "outer": 1, "info": "base"},
        }, di),
    )

    result = taper_grading.grading_alarm_taper_shape(data_integration)

    assert result.grad == 3
    assert captured[0].out_taper_max_value == 80.0
    metadata = json.loads(captured[0].data)
    assert metadata["ignored_outer_mm"] == 2.0
    assert metadata["applied_ignored_outer_mm"] == 0.0
    assert metadata["outer_skip_count"] == 0


def test_grading_alarm_taper_shape_ignores_low_value_edge_noise_before_split(monkeypatch):
    ray_line = np.array([[i, 0, 100] for i in range(12)], dtype=float)
    ray_line[:2, 2] = 5
    ray_line[-2:, 2] = 5
    ray_line[7, 2] = 260
    line_data = SimpleNamespace(
        rotation_angle=0,
        ray_line=ray_line,
        outer_max_point=_point(7, 0, 260),
        outer_min_point=_point(6, 0, 100),
        inner_max_point=_point(5, 0, 100),
        inner_min_point=_point(2, 0, 100),
    )
    data_integration = FakeDataIntegration()
    data_integration.alarmData = SimpleNamespace(lineDataDict={0: line_data})

    captured = []
    monkeypatch.setattr(taper_grading, "add_obj", captured.append)
    monkeypatch.setattr(
        taper_grading.alarmConfigProperty,
        "get_taper_shape_config",
        lambda di: TaperShapeConfig({
            "Base": {"name": "base", "height": [60, 80], "inner": 0, "outer": 0, "info": "base"},
        }, di),
    )

    result = taper_grading.grading_alarm_taper_shape(data_integration)

    assert result.grad == 3
    assert captured[0].out_taper_max_value == 80.0
    assert captured[0].in_taper_max_value == 0.0


def test_grading_alarm_taper_shape_accepts_sequence_line_data(monkeypatch):
    line_positive = SimpleNamespace(
        rotation_angle=20,
        outer_max_point=_point(10, 20, 260),
        outer_min_point=_point(11, 21, 100),
        inner_max_point=_point(12, 22, 100),
        inner_min_point=_point(13, 23, 100),
    )
    data_integration = FakeDataIntegration()
    data_integration.alarmData = SimpleNamespace(lineDataDict=[line_positive])

    captured = []
    monkeypatch.setattr(taper_grading, "add_obj", captured.append)
    monkeypatch.setattr(
        taper_grading.alarmConfigProperty,
        "get_taper_shape_config",
        lambda di: TaperShapeConfig({
            "Base": {"name": "base", "height": [60, 80], "inner": 0, "outer": 0, "info": "base"},
        }, di),
    )

    result = taper_grading.grading_alarm_taper_shape(data_integration)

    assert result.grad == 3
    assert captured[0].out_taper_max_value == 80.0


def test_grading_alarm_taper_shape_invalid_line_container_returns_failure(monkeypatch):
    data_integration = FakeDataIntegration()
    data_integration.alarmData = SimpleNamespace(lineDataDict="invalid")

    captured = []
    monkeypatch.setattr(taper_grading, "add_obj", captured.append)
    monkeypatch.setattr(
        taper_grading.alarmConfigProperty,
        "get_taper_shape_config",
        lambda di: TaperShapeConfig({
            "Base": {"name": "base", "height": [60, 80], "inner": 0, "outer": 0, "info": "base"},
        }, di),
    )

    result = taper_grading.grading_alarm_taper_shape(data_integration)

    assert result.grad == 3
    assert "有效线数据" in result.errorMsg
    assert "lineDataDict容器无效" in result.errorMsg
    assert captured == []


def test_grading_alarm_taper_shape_reports_invalid_line_metrics(monkeypatch):
    malformed_line = SimpleNamespace(
        rotation_angle=10,
        ray_line=np.array([0, 0, 260], dtype=float),
    )
    data_integration = FakeDataIntegration()
    data_integration.alarmData = SimpleNamespace(lineDataDict={10: malformed_line})

    captured = []
    monkeypatch.setattr(taper_grading, "add_obj", captured.append)
    monkeypatch.setattr(
        taper_grading.alarmConfigProperty,
        "get_taper_shape_config",
        lambda di: TaperShapeConfig({
            "Base": {"name": "base", "height": [60, 80], "inner": 0, "outer": 0, "info": "base"},
        }, di),
    )

    result = taper_grading.grading_alarm_taper_shape(data_integration)

    assert result.grad == 3
    assert "无有效线数据" in result.errorMsg
    assert "10度: 无有效塔形线指标" in result.errorMsg
    assert data_integration.alarmData.taper_shape_grading_errors == [
        "10度: 无有效塔形线指标"
    ]
    assert captured == []


def test_grading_alarm_taper_shape_reports_detection_errors(monkeypatch):
    data_integration = FakeDataIntegration()
    data_integration.alarmData = SimpleNamespace(
        lineDataDict={},
        taper_shape_errors=[
            "0度: center out of image bounds",
            "10度: 3D/mask shape mismatch",
            "20度: line data empty",
            "30度: line data empty",
        ],
    )

    captured = []
    monkeypatch.setattr(taper_grading, "add_obj", captured.append)
    monkeypatch.setattr(
        taper_grading.alarmConfigProperty,
        "get_taper_shape_config",
        lambda di: TaperShapeConfig({
            "Base": {"name": "base", "height": [60, 80], "inner": 0, "outer": 0, "info": "base"},
        }, di),
    )

    result = taper_grading.grading_alarm_taper_shape(data_integration)

    assert result.grad == 3
    assert "无有效线数据" in result.errorMsg
    assert "0度: center out of image bounds" in result.errorMsg
    assert "10度: 3D/mask shape mismatch" in result.errorMsg
    assert "另有1个角度失败" in result.errorMsg
    assert captured == []


def test_line_data_detection_keeps_boundary_with_inner_mask_holes():
    line_data = LineData(
        npy_data=np.zeros((1, 10), dtype=np.int32),
        mask_image=np.ones((1, 10), dtype=np.uint8) * 255,
        p1=Point2D(0, 0),
        p2=Point2D(9, 0),
    )
    line_data._ray_data_ = np.array([
        [0, 0, 100],
        [1, 0, 0],
        [2, 0, 0],
        [3, 0, 0],
        [4, 0, 100],
        [5, 0, 260],
        [6, 0, 100],
        [7, 0, 100],
        [8, 0, 100],
        [9, 0, 100],
    ], dtype=np.int32)

    line_data.det_taper_shape()

    assert line_data.inner_max_point.x == 4
    assert line_data.inner_max_point.z == 100.0
    assert line_data.outer_max_point.x == 5
    assert line_data.outer_max_point.z == 260.0


def test_line_data_detection_rejects_sparse_side_points():
    line_data = LineData(
        npy_data=np.zeros((1, 4), dtype=np.int32),
        mask_image=np.ones((1, 4), dtype=np.uint8) * 255,
        p1=Point2D(0, 0),
        p2=Point2D(3, 0),
    )
    line_data._ray_data_ = np.array([
        [0, 0, 100],
        [1, 0, 0],
        [2, 0, 0],
        [3, 0, 260],
    ], dtype=np.int32)

    with pytest.raises(ValueError, match="塔形线有效点不足 inner=1 outer=1 min=2"):
        line_data.det_taper_shape()


def test_line_data_detection_rejects_low_coverage_line():
    line_data = LineData(
        npy_data=np.zeros((1, 12), dtype=np.int32),
        mask_image=np.ones((1, 12), dtype=np.uint8) * 255,
        p1=Point2D(0, 0),
        p2=Point2D(11, 0),
    )
    line_data._ray_data_ = np.array([
        [0, 0, 100],
        [1, 0, 100],
        [2, 0, 0],
        [3, 0, 0],
        [4, 0, 0],
        [5, 0, 0],
        [6, 0, 0],
        [7, 0, 0],
        [8, 0, 0],
        [9, 0, 0],
        [10, 0, 260],
        [11, 0, 100],
    ], dtype=np.int32)

    with pytest.raises(ValueError, match="塔形线有效覆盖率不足 coverage=0.33 min=0.50"):
        line_data.det_taper_shape()


def test_line_data_detection_rejects_low_side_coverage_line():
    line_data = LineData(
        npy_data=np.zeros((1, 12), dtype=np.int32),
        mask_image=np.ones((1, 12), dtype=np.uint8) * 255,
        p1=Point2D(0, 0),
        p2=Point2D(11, 0),
    )
    line_data._ray_data_ = np.array([
        [0, 0, 100],
        [1, 0, 0],
        [2, 0, 0],
        [3, 0, 0],
        [4, 0, 0],
        [5, 0, 100],
        [6, 0, 100],
        [7, 0, 100],
        [8, 0, 260],
        [9, 0, 100],
        [10, 0, 100],
        [11, 0, 100],
    ], dtype=np.int32)

    with pytest.raises(
            ValueError,
            match="塔形线单侧有效覆盖率不足 inner=0.33 outer=1.00 min=0.40"):
        line_data.det_taper_shape()


def test_line_data_unit_distance_uses_intervals_between_points():
    line_data = LineData(
        npy_data=np.zeros((1, 5), dtype=np.int32),
        mask_image=np.ones((1, 5), dtype=np.uint8) * 255,
        p1=Point2D(0, 0),
        p2=Point2D(4, 0),
    )
    line_data._ray_data_ = np.array([
        [0, 0, 100],
        [1, 0, 0],
        [2, 0, 0],
        [3, 0, 100],
        [4, 0, 100],
    ], dtype=np.int32)
    line_data.dataIntegration = SimpleNamespace(
        x_to_mm=lambda value: float(value),
        point_to_mm=lambda points: points.astype(float),
        zero_mm=lambda: 10.0,
    )

    assert line_data.count == 5
    assert line_data.length_mm == 4.0
    assert line_data.unit_distance_mm == 1.0
    assert line_data.none_data_sub == [(1, 2, 1.0, 2.0)]
    assert line_data.max_zero_width_mm == 2.0


def test_line_data_length_mm_uses_y_scale_for_vertical_lines():
    line_data = LineData(
        npy_data=np.zeros((5, 1), dtype=np.int32),
        mask_image=np.ones((5, 1), dtype=np.uint8) * 255,
        p1=Point2D(0, 0),
        p2=Point2D(0, 4),
    )
    line_data._ray_data_ = np.array([
        [0, 0, 100],
        [0, 1, 0],
        [0, 2, 0],
        [0, 3, 100],
        [0, 4, 100],
    ], dtype=np.int32)
    line_data.dataIntegration = SimpleNamespace(
        scan3dCoordinateScaleX=0.5,
        scan3dCoordinateScaleY=2.0,
        x_to_mm=lambda value: float(value) * 0.5,
        point_to_mm=lambda points: points.astype(float),
        zero_mm=lambda: 10.0,
    )

    assert line_data.length_mm == 8.0
    assert line_data.unit_distance_mm == 2.0
    assert line_data.none_data_sub == [(1, 2, 2.0, 4.0)]
    assert line_data.max_zero_width_mm == 4.0


def test_line_data_model_sanitizes_non_finite_ray_line_json():
    line_data = LineData(
        npy_data=np.zeros((1, 5), dtype=np.int32),
        mask_image=np.ones((1, 5), dtype=np.uint8) * 255,
        p1=Point2D(0, 0),
        p2=Point2D(4, 0),
    )
    line_data._ray_data_ = np.array([
        [0, 0, 100],
        [1, 0, np.inf],
        [2, 0, np.nan],
        [3, 0, 100],
        [4, 0, 100],
    ], dtype=float)
    line_data.rotation_angle = 0
    line_data.inner_min_point = _point(0, 0, 100)
    line_data.inner_max_point = _point(0, 0, 100)
    line_data.outer_min_point = _point(4, 0, 100)
    line_data.outer_max_point = _point(4, 0, 100)

    data_integration = SimpleNamespace(
        secondary_coil_id=1001,
        key="S",
        width=5,
        height=1,
        median_3d_mm=100.0,
        alarmData=SimpleNamespace(flatRollData=SimpleNamespace(get_center=lambda: Point2D(2, 0))),
        z_to_mm=lambda z: float(z),
    )

    model = line_data.line_data_model(data_integration)

    assert "Infinity" not in model.data
    assert "NaN" not in model.data
    line_json = json.loads(model.data)
    assert line_json[1][2] == 0.0
    assert line_json[2][2] == 0.0


def test_line_data_model_accepts_tuple_center():
    line_data = LineData(
        npy_data=np.zeros((1, 5), dtype=np.int32),
        mask_image=np.ones((1, 5), dtype=np.uint8) * 255,
        p1=Point2D(0, 0),
        p2=Point2D(4, 0),
    )
    line_data._ray_data_ = np.array([
        [0, 0, 100],
        [1, 0, 100],
        [2, 0, 100],
        [3, 0, 100],
        [4, 0, 100],
    ], dtype=float)
    line_data.rotation_angle = 0
    line_data.inner_min_point = _point(0, 0, 100)
    line_data.inner_max_point = _point(1, 0, 100)
    line_data.outer_min_point = _point(3, 0, 100)
    line_data.outer_max_point = _point(4, 0, 100)

    data_integration = SimpleNamespace(
        secondary_coil_id=1001,
        key="S",
        width=5,
        height=1,
        median_3d_mm=100.0,
        alarmData=SimpleNamespace(flatRollData=SimpleNamespace(get_center=lambda: (2, 0))),
        z_to_mm=lambda z: float(z),
    )

    model = line_data.line_data_model(data_integration)

    assert model.center_x == 2.0
    assert model.center_y == 0.0


def test_line_data_model_accepts_mapping_center():
    line_data = LineData(
        npy_data=np.zeros((1, 5), dtype=np.int32),
        mask_image=np.ones((1, 5), dtype=np.uint8) * 255,
        p1=Point2D(0, 0),
        p2=Point2D(4, 0),
    )
    line_data._ray_data_ = np.array([
        [0, 0, 100],
        [1, 0, 100],
        [2, 0, 100],
        [3, 0, 100],
        [4, 0, 100],
    ], dtype=float)
    line_data.rotation_angle = 0
    line_data.inner_min_point = _point(0, 0, 100)
    line_data.inner_max_point = _point(1, 0, 100)
    line_data.outer_min_point = _point(3, 0, 100)
    line_data.outer_max_point = _point(4, 0, 100)

    data_integration = SimpleNamespace(
        secondary_coil_id=1001,
        key="S",
        width=5,
        height=1,
        median_3d_mm=100.0,
        alarmData=SimpleNamespace(
            flatRollData=SimpleNamespace(get_center=lambda: {"x": "2.0", "y": 0})
        ),
        z_to_mm=lambda z: float(z),
    )

    model = line_data.line_data_model(data_integration)

    assert model.center_x == 2.0
    assert model.center_y == 0.0


def test_line_data_model_accepts_center_object_aliases():
    line_data = LineData(
        npy_data=np.zeros((1, 5), dtype=np.int32),
        mask_image=np.ones((1, 5), dtype=np.uint8) * 255,
        p1=Point2D(0, 0),
        p2=Point2D(4, 0),
    )
    line_data._ray_data_ = np.array([
        [0, 0, 100],
        [1, 0, 100],
        [2, 0, 100],
        [3, 0, 100],
        [4, 0, 100],
    ], dtype=float)
    line_data.rotation_angle = 0
    line_data.inner_min_point = _point(0, 0, 100)
    line_data.inner_max_point = _point(1, 0, 100)
    line_data.outer_min_point = _point(3, 0, 100)
    line_data.outer_max_point = _point(4, 0, 100)

    data_integration = SimpleNamespace(
        secondary_coil_id=1001,
        key="S",
        width=5,
        height=1,
        median_3d_mm=100.0,
        alarmData=SimpleNamespace(
            flatRollData=SimpleNamespace(
                get_center=lambda: SimpleNamespace(centerX="2.0", centerY=0)
            )
        ),
        z_to_mm=lambda z: float(z),
    )

    model = line_data.line_data_model(data_integration)

    assert model.center_x == 2.0
    assert model.center_y == 0.0


def test_generate_error_image_uses_absolute_thresholds(tmp_path):
    npy_data = np.array([[1989, 2000, 2021]], dtype=np.uint16)

    assert generate_error_image(
        npy_data=npy_data,
        png_dir=tmp_path,
        median_z_int=2000,
        threshold_down=-10,
        threshold_up=20,
        scale_factor=1.0,
    )

    image = Image.open(tmp_path / "Error.png").convert("RGBA")
    assert image.getpixel((0, 0)) == (0, 0, 255, 255)
    assert image.getpixel((1, 0)) == (0, 0, 0, 0)
    assert image.getpixel((2, 0)) == (255, 0, 0, 255)
    metadata = json.loads((tmp_path / "Error.json").read_text(encoding="utf-8"))
    assert metadata["threshold_down"] == 10.0
    assert metadata["threshold_up"] == 20.0
    assert metadata["scale_factor"] == 1.0


def test_taper_error_image_uses_first_alarm_threshold():
    assert taper_error_threshold_from_limits([60, 80]) == (60.0, 60.0)
    assert taper_error_threshold_from_limits([]) == (60.0, 60.0)
    assert taper_error_threshold_from_limits([np.inf, "nan"]) == (60.0, 60.0)
    assert taper_error_threshold_from_limits([np.inf, 90]) == (90.0, 90.0)
    assert taper_error_threshold_from_limits(["bad", None], 120) == (120.0, 120.0)
    assert taper_error_threshold_from_limits("50, 80") == (50.0, 50.0)
    assert taper_error_threshold_from_limits("[45；90]") == (45.0, 45.0)


def test_taper_error_threshold_ignores_overflowing_values():
    class OverflowingValue:
        def __float__(self):
            raise OverflowError("too large")

    assert taper_error_threshold_from_limits([OverflowingValue()], 120) == (120.0, 120.0)


def test_detection_taper_shape_skips_zero_division_angle(monkeypatch):
    alarm_data = SimpleNamespace()
    data_integration = SimpleNamespace(
        coilId=1001,
        surface="S",
        alarmData=alarm_data,
    )
    valid_line = SimpleNamespace(rotation_angle=180)
    warnings = []

    def fake_detection_by_angle(_data_integration, rotation_angle):
        if rotation_angle == 0:
            raise ZeroDivisionError("degenerate ray")
        return valid_line

    monkeypatch.setattr(taper_processing, "TAPER_ROTATION_STEP", 180)
    monkeypatch.setattr(
        taper_processing,
        "detection_taper_shape_by_rotation_angle",
        fake_detection_by_angle,
    )
    monkeypatch.setattr(taper_processing.logger, "warning", warnings.append)

    line_data_dict = taper_processing._detection_taper_shape_(data_integration)

    assert line_data_dict == {180: valid_line}
    assert alarm_data.taper_shape_attempt_count == 2
    assert alarm_data.taper_shape_errors == ["0度: degenerate ray"]
    assert len(warnings) == 1
    assert "塔形角度 0 跳过" in warnings[0]


def test_unsupported_taper_shape_type_falls_back_to_line(monkeypatch):
    captured = []
    data_integration = SimpleNamespace(
        alarmData=SimpleNamespace(set_line_data_dict=captured.append)
    )

    monkeypatch.setattr(taper_processing.Globs.control, "taper_shape_type", DetectionTaperShapeType.WK_TYPE)
    monkeypatch.setattr(taper_processing, "_detection_taper_shape_", lambda item: {"line": item})
    monkeypatch.setattr(
        taper_processing,
        "_detectionTaperShapeA_",
        lambda item: (_ for _ in ()).throw(AssertionError("WK branch should not run")),
    )

    taper_processing._detection_taper_shape_all_([data_integration])

    assert captured == [{"line": data_integration}]


def test_string_none_taper_shape_type_disables_line_detection(monkeypatch):
    captured = []
    data_integration = SimpleNamespace(
        alarmData=SimpleNamespace(
            taper_shape_disabled=False,
            set_line_data_dict=captured.append,
        )
    )

    monkeypatch.setattr(taper_processing.Globs.control, "taper_shape_type", "none")
    monkeypatch.setattr(
        taper_processing,
        "_detection_taper_shape_",
        lambda item: (_ for _ in ()).throw(AssertionError("LINE branch should not run")),
    )

    taper_processing._detection_taper_shape_all_([data_integration])

    assert captured == [{}]
    assert data_integration.alarmData.taper_shape_disabled is True


@pytest.mark.parametrize("value", ["false", "False", "off", "disabled", "disable", "no"])
def test_boolean_string_taper_shape_type_disables_line_detection(monkeypatch, value):
    captured = []
    data_integration = SimpleNamespace(
        alarmData=SimpleNamespace(
            taper_shape_disabled=False,
            set_line_data_dict=captured.append,
        )
    )

    monkeypatch.setattr(taper_processing.Globs.control, "taper_shape_type", value)
    monkeypatch.setattr(
        taper_processing,
        "_detection_taper_shape_",
        lambda item: (_ for _ in ()).throw(AssertionError("LINE branch should not run")),
    )

    taper_processing._detection_taper_shape_all_([data_integration])

    assert captured == [{}]
    assert data_integration.alarmData.taper_shape_disabled is True


@pytest.mark.parametrize("value", ["true", "True", "on", "enabled", "enable", "yes", "line"])
def test_boolean_string_taper_shape_type_enables_line_detection(monkeypatch, value):
    captured = []
    data_integration = SimpleNamespace(
        alarmData=SimpleNamespace(
            taper_shape_disabled=True,
            set_line_data_dict=captured.append,
        )
    )

    monkeypatch.setattr(taper_processing.Globs.control, "taper_shape_type", value)
    monkeypatch.setattr(taper_processing, "_detection_taper_shape_", lambda item: {"line": item})

    taper_processing._detection_taper_shape_all_([data_integration])

    assert captured == [{"line": data_integration}]
    assert data_integration.alarmData.taper_shape_disabled is False


def test_disabled_taper_shape_grades_normal_without_alarm_record(monkeypatch):
    data_integration = FakeDataIntegration()
    data_integration.alarmData = SimpleNamespace(lineDataDict={}, taper_shape_disabled=True)

    captured = []
    monkeypatch.setattr(taper_grading, "add_obj", captured.append)
    monkeypatch.setattr(
        taper_grading.alarmConfigProperty,
        "get_taper_shape_config",
        lambda di: TaperShapeConfig({
            "Base": {"name": "base", "height": [60, 80], "inner": 0, "outer": 0, "info": "base"},
        }, di),
    )

    result = taper_grading.grading_alarm_taper_shape(data_integration)

    assert result.grad == 1
    assert result.errorMsg == "塔形检测关闭"
    assert captured == []


def test_zero_taper_shape_type_disables_line_detection(monkeypatch):
    for value in (0, "0", "0.0", "+0.0", DetectionTaperShapeType(0)):
        captured = []
        data_integration = SimpleNamespace(
            alarmData=SimpleNamespace(
                taper_shape_disabled=False,
                set_line_data_dict=captured.append,
            )
        )

        monkeypatch.setattr(taper_processing.Globs.control, "taper_shape_type", value)
        monkeypatch.setattr(
            taper_processing,
            "_detection_taper_shape_",
            lambda item: (_ for _ in ()).throw(AssertionError("LINE branch should not run")),
        )

        taper_processing._detection_taper_shape_all_([data_integration])

        assert captured == [{}]
        assert data_integration.alarmData.taper_shape_disabled is True


def test_boolean_taper_shape_type_controls_line_detection(monkeypatch):
    enabled_captured = []
    enabled_alarm_data = SimpleNamespace(
        taper_shape_disabled=True,
        taper_shape_errors=["old detection error"],
        taper_shape_grading_errors=["old grading error"],
        set_line_data_dict=enabled_captured.append,
    )
    enabled_data_integration = SimpleNamespace(alarmData=enabled_alarm_data)

    monkeypatch.setattr(taper_processing.Globs.control, "taper_shape_type", True)
    monkeypatch.setattr(taper_processing, "_detection_taper_shape_", lambda item: {"line": item})

    taper_processing._detection_taper_shape_all_([enabled_data_integration])

    assert enabled_captured == [{"line": enabled_data_integration}]
    assert enabled_alarm_data.taper_shape_disabled is False
    assert enabled_alarm_data.taper_shape_errors == []
    assert enabled_alarm_data.taper_shape_grading_errors == []

    disabled_captured = []
    disabled_alarm_data = SimpleNamespace(
        taper_shape_disabled=False,
        taper_shape_errors=["old detection error"],
        taper_shape_grading_errors=["old grading error"],
        set_line_data_dict=disabled_captured.append,
    )
    disabled_data_integration = SimpleNamespace(alarmData=disabled_alarm_data)

    monkeypatch.setattr(taper_processing.Globs.control, "taper_shape_type", False)
    monkeypatch.setattr(
        taper_processing,
        "_detection_taper_shape_",
        lambda item: (_ for _ in ()).throw(AssertionError("LINE branch should not run")),
    )

    taper_processing._detection_taper_shape_all_([disabled_data_integration])

    assert disabled_captured == [{}]
    assert disabled_alarm_data.taper_shape_disabled is True
    assert disabled_alarm_data.taper_shape_errors == []
    assert disabled_alarm_data.taper_shape_grading_errors == []


def test_invalid_taper_shape_type_falls_back_to_line(monkeypatch):
    captured = []
    data_integration = SimpleNamespace(
        alarmData=SimpleNamespace(set_line_data_dict=captured.append)
    )

    monkeypatch.setattr(taper_processing.Globs.control, "taper_shape_type", "BAD_VALUE")
    monkeypatch.setattr(taper_processing, "_detection_taper_shape_", lambda item: {"line": item})

    taper_processing._detection_taper_shape_all_([data_integration])

    assert captured == [{"line": data_integration}]


@pytest.mark.parametrize("value", ["8.0", "+8", " 8.0 "])
def test_numeric_string_taper_shape_type_enables_line(monkeypatch, value):
    captured = []
    warnings = []
    data_integration = SimpleNamespace(
        alarmData=SimpleNamespace(set_line_data_dict=captured.append)
    )

    monkeypatch.setattr(taper_processing.Globs.control, "taper_shape_type", value)
    monkeypatch.setattr(taper_processing, "_detection_taper_shape_", lambda item: {"line": item})
    monkeypatch.setattr(taper_processing.logger, "warning", warnings.append)

    taper_processing._detection_taper_shape_all_([data_integration])

    assert captured == [{"line": data_integration}]
    assert warnings == []


def test_negative_numeric_taper_shape_type_falls_back_to_line(monkeypatch):
    captured = []
    warnings = []
    data_integration = SimpleNamespace(
        alarmData=SimpleNamespace(set_line_data_dict=captured.append)
    )

    monkeypatch.setattr(taper_processing.Globs.control, "taper_shape_type", -1)
    monkeypatch.setattr(taper_processing, "_detection_taper_shape_", lambda item: {"line": item})
    monkeypatch.setattr(taper_processing.logger, "warning", warnings.append)

    taper_processing._detection_taper_shape_all_([data_integration])

    assert captured == [{"line": data_integration}]
    assert any("invalid taper_shape_type=-1" in warning for warning in warnings)


def test_line_with_unsupported_taper_shape_type_warns_and_uses_line(monkeypatch):
    captured = []
    warnings = []
    data_integration = SimpleNamespace(
        alarmData=SimpleNamespace(set_line_data_dict=captured.append)
    )

    monkeypatch.setattr(
        taper_processing.Globs.control,
        "taper_shape_type",
        "line|16.0",
    )
    monkeypatch.setattr(taper_processing, "_detection_taper_shape_", lambda item: {"line": item})
    monkeypatch.setattr(taper_processing.logger, "warning", warnings.append)

    taper_processing._detection_taper_shape_all_([data_integration])

    assert captured == [{"line": data_integration}]
    assert any("use LINE_TYPE branch only" in warning for warning in warnings)


def test_taper_shape_all_accepts_single_data_integration(monkeypatch):
    captured = []
    data_integration = SimpleNamespace(
        alarmData=SimpleNamespace(
            taper_shape_disabled=False,
            set_line_data_dict=captured.append,
        )
    )

    monkeypatch.setattr(taper_processing.Globs.control, "taper_shape_type", DetectionTaperShapeType.LINE_TYPE)
    monkeypatch.setattr(taper_processing, "_detection_taper_shape_", lambda item: {"line": item})

    taper_processing._detection_taper_shape_all_(data_integration)

    assert captured == [{"line": data_integration}]
    assert data_integration.alarmData.taper_shape_disabled is False
