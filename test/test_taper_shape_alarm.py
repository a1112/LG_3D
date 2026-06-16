import sys
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "app", ROOT / "app" / "Base", ROOT / "app" / "algorithm_runtime"):
    sys.path.insert(0, str(path))

from AlarmDetection.Configs.TaperShapeConfig import TaperShapeConfig
from Base.utils.cache_generator import generate_error_image
from Base.property.Data3D import find_line_max_min
import AlarmDetection.Grading.alarm_taper_shape as taper_grading
import AlarmDetection.DataProcessing.TaperShape as taper_processing
from Base.property.Types import DetectionTaperShapeType


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


def test_taper_shape_config_uses_next_code_override():
    config = TaperShapeConfig({
        "Base": {"name": "base", "height": [60, 80], "inner": 0, "outer": 0, "info": "base"},
        "2": {"name": "code2", "height": [50, 70], "inner": 3, "outer": 1, "info": "code2"},
    }, FakeDataIntegration())

    assert config.get_config().get_config() == ("code2", [50, 70], 3, 1, "code2")


def test_find_line_max_min_filters_single_point_spike():
    line = np.array([[i, 0, 1000] for i in range(120)], dtype=float)
    line[119, 2] = 50000

    max_point, min_point = find_line_max_min(line, 10, use_iqr=True, type_="outer")

    assert max_point.z == 1000.0
    assert min_point.z == 1000.0


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
