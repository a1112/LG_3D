"""Offline regressions for calibrated geometry and the alarm pipeline."""
import importlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import cv2
import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "app", ROOT / "app" / "Base", ROOT / "app" / "algorithm_runtime"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from AlarmDetection.Configs.FlatRollConfig import FlatRollConfig
from AlarmDetection.Configs.LooseCoilConfig import LooseCoilConfig
from AlarmDetection.DataProcessing.AlarmFlatRoll import get_data, get_inner_circle_contour
from AlarmDetection.DataProcessing.AlarmLooseCoil import _detectionAlarmLooseCoilAll_
from AlarmDetection.Grading.alarm_defects import grading_alarm_defects
from AlarmDetection.Grading.alarm_loose_coil import grading_alarm_loose_coil
from AlarmDetection.Result.AlarmData import AlarmData
from AlarmDetection.Result.FlatRollData import FlatRollData
from AlarmDetection.property import alarmConfigProperty
from Base.property.Data3D import LineData


def _annulus():
    mask = np.zeros((128, 128), dtype=np.uint8)
    cv2.circle(mask, (64, 64), 55, 255, -1)
    cv2.circle(mask, (64, 64), 20, 0, -1)
    return mask


@pytest.mark.parametrize("dtype", [np.uint8, np.float32, np.bool_])
def test_circle_detector_accepts_binary_mask_representations(dtype):
    mask = (_annulus() > 0).astype(dtype)
    outer, inner = get_data(mask)
    assert inner.ellipse.center_x == pytest.approx(64, abs=1)
    assert inner.ellipse.center_y == pytest.approx(64, abs=1)
    assert inner.ellipse.width == pytest.approx(40, abs=2)
    assert outer.ellipse.width == pytest.approx(110, abs=2)


@pytest.mark.parametrize("mask", [np.zeros((64, 64), np.uint8), np.ones((64, 64), np.uint8)])
def test_circle_detector_rejects_missing_eye_instead_of_using_image_border(mask):
    with pytest.raises(ValueError):
        get_inner_circle_contour(mask)


def test_solid_disk_is_not_misidentified_as_its_own_inner_eye():
    mask = np.zeros((128, 128), np.uint8)
    cv2.circle(mask, (64, 64), 55, 255, -1)
    with pytest.raises(ValueError):
        get_inner_circle_contour(mask)


@pytest.mark.parametrize("config_cls, base, override, expected", [
    (FlatRollConfig, {"min": 600, "max": 780}, {"min": 705}, ("base", 780, 705, "rule")),
    (LooseCoilConfig, {"width": 25}, {"width": 12}, ("base", 12, "rule")),
])
@pytest.mark.parametrize("base_key", ["Base", "base"])
def test_geometry_configs_honor_destination_overrides(config_cls, base, override, expected, base_key):
    source = {base_key: {"name": "base", "info": "rule", **base}, "2": override}
    original = json.dumps(source)
    actual = config_cls(source, SimpleNamespace(next_code="2")).get_config().get_config()
    assert actual == expected
    assert json.dumps(source) == original


@pytest.mark.parametrize("angle, expected", [(0, 40), (90, 20), (45, 24.063722255)])
def test_flat_roll_diameter_uses_rotated_anisotropic_calibration(angle, expected):
    integration = SimpleNamespace(scan3dCoordinateScaleX=2.0, scan3dCoordinateScaleY=1.0)
    inner = SimpleNamespace(ellipse=SimpleNamespace(width=20, height=40, rotation_angle=angle))
    result = FlatRollData(integration, inner)
    assert result.inner_diameter_mm() == pytest.approx(expected)


def _line_with_gap(scale_z=0.01):
    line = LineData.__new__(LineData)
    line._ray_line_ = np.array([[0, 0, 100], [1, 0, 100], [2, 0, 0],
                               [3, 0, np.nan], [4, 0, 100]], dtype=float)
    line.dataIntegration = SimpleNamespace(scan3dCoordinateScaleX=0.3,
                                           scan3dCoordinateScaleY=0.7,
                                           scan3dCoordinateScaleZ=scale_z)
    line.rotation_angle = 0
    return line


@pytest.mark.parametrize("scale_z", [0.01, 1.0, 100.0])
def test_loose_gap_validity_is_independent_of_depth_calibration(scale_z):
    line = _line_with_gap(scale_z)
    assert line.none_data_sub == [(2, 2, pytest.approx(0.6), pytest.approx(0.6))]
    assert line.max_zero_width_mm == pytest.approx(0.6)


def test_loose_coil_saves_actual_gap_and_destination_limit(monkeypatch):
    module = importlib.import_module("AlarmDetection.Grading.alarm_loose_coil")
    saved = []
    monkeypatch.setattr(module, "addAlarmLooseCoil", saved.append)
    monkeypatch.setattr(alarmConfigProperty, "config", {"LooseCoil": {
        "Base": {"width": 25}, "2": {"name": "code2", "width": 0.5}}})
    integration = SimpleNamespace(coilId=101, surface="S", next_code="2")
    integration.alarmData = AlarmData(integration)
    integration.alarmData.lineDataDict = {0: _line_with_gap()}
    _detectionAlarmLooseCoilAll_([integration])
    result = grading_alarm_loose_coil(integration)
    assert result.grad == 3
    assert len(saved) == 1
    assert saved[0].max_width == pytest.approx(0.6)
    assert saved[0].rotation_angle == 0
    assert saved[0].level == 3
    payload = json.loads(saved[0].data)
    assert payload["max_width_unit"] == "mm"
    assert payload["width_limit_mm"] == 0.5
    assert payload["measurements"][0]["segments"][0][:2] == [2, 2]


def test_loose_coil_missing_lines_cannot_report_normal(monkeypatch):
    module = importlib.import_module("AlarmDetection.Grading.alarm_loose_coil")
    saved = []
    monkeypatch.setattr(module, "addAlarmLooseCoil", saved.append)
    integration = SimpleNamespace(coilId=101, surface="S", next_code="2")
    integration.alarmData = AlarmData(integration)
    result = grading_alarm_loose_coil(integration)
    assert result.grad == 3
    assert "无有效" in result.errorMsg
    assert saved == []


def test_explicitly_disabled_radial_detection_remains_disabled(monkeypatch):
    integration = SimpleNamespace(coilId=101, surface="S", next_code="2")
    integration.alarmData = AlarmData(integration)
    integration.alarmData.taper_shape_disabled = True
    result = grading_alarm_loose_coil(integration)
    assert result.grad == 1
    assert "检测关闭" in result.errorMsg


def test_defect_grading_honors_shared_visibility_and_severity(monkeypatch):
    import Base.CONFIG as config
    monkeypatch.setattr(config, "defectClassesProperty", SimpleNamespace(
        data={"visible": {"level": 4, "show": True}, "hidden": {"level": 5, "show": False}},
        default={"show": True},
    ))
    integration = SimpleNamespace(defect_dict={"visible": [(0, 0, 10, 10, 0, 0.9)],
                                             "hidden": [(10, 0, 20, 10, 1, 0.9)]})
    result = grading_alarm_defects(integration)
    assert result.grad == 4
    assert "visible" in result.errorMsg
    assert "hidden" not in result.errorMsg
    assert "1个缺陷" in result.errorMsg


def test_defect_missing_results_differs_from_successful_empty_result():
    missing = SimpleNamespace(defect_dict=None)
    assert grading_alarm_defects(missing).grad == 3
    assert missing.alarm_processing_errors == ["defect: 缺陷检测未完成: 无有效检测结果"]
    assert grading_alarm_defects(SimpleNamespace(defect_dict={})).grad == 1


def test_taper_detection_accepts_boolean_mask_through_real_line_sampler():
    from AlarmDetection.DataProcessing.TaperShapeLine import detection_taper_shape_by_rotation_angle
    integration = _integration("S")
    outer, inner = get_data(integration.npy_mask)
    integration.alarmData.flatRollData = FlatRollData(integration, inner, outer)
    integration.npy_mask = integration.npy_mask.astype(bool)
    line = detection_taper_shape_by_rotation_angle(integration, 0)
    assert line.inner_min_point.z == 100
    assert line.outer_max_point.z == 100


def test_pipeline_runs_second_surface_after_first_surface_stage_failure(monkeypatch):
    pipeline = importlib.import_module("AlarmDetection.detection")
    calls = []

    def flat_stage(items):
        calls.append(("flat", items[0].surface))
        if items[0].surface == "S":
            raise ValueError("broken surface")

    monkeypatch.setattr(pipeline, "_detectionAlarmFlatRollAll_", flat_stage)
    for name in ("_detection_taper_shape_all_", "_detectionAlarmLooseCoilAll_",
                 "_detectionAlarmDefectAll_", "grading_all"):
        monkeypatch.setattr(pipeline, name, lambda items, name=name: calls.append((name, items[0].surface)))
    surfaces = iter([SimpleNamespace(coilId=1, surface="S"), SimpleNamespace(coilId=1, surface="L")])
    errors = pipeline.detection_all(surfaces)
    assert calls[:2] == [("flat", "S"), ("flat", "L")]
    assert len(calls) == 10
    assert calls[-2:] == [("grading_all", "S"), ("grading_all", "L")]
    assert errors == {"S": ["flat_roll: broken surface"]}


def _integration(surface):
    mask = _annulus()
    depth = np.where(mask > 0, 100.0, 0.0)
    integration = SimpleNamespace(
        coilId=101, secondary_coil_id=101, surface=surface, key=surface,
        next_code="2", next_name="test", npy_mask=mask, npy_data=depth,
        width=128, height=128, median_3d_mm=50.0,
        scan3dCoordinateScaleX=1.0, scan3dCoordinateScaleY=1.0,
        scan3dCoordinateScaleZ=0.5, scan3dCoordinateOffsetZ=0.0,
        accuracy_x=1.0, accuracy_y=1.0,
        currentSecondaryCoil=SimpleNamespace(Thickness=0), coilData={},
        z_to_mm=lambda z: float(z) * 0.5, x_to_mm=lambda x: float(x),
        defect_dict={},
    )
    integration.alarmData = AlarmData(integration)
    return integration


def test_offline_annular_depth_runs_detection_grading_and_persistence(monkeypatch):
    import Base.CONFIG as config
    pipeline = importlib.import_module("AlarmDetection.detection")
    taper_module = importlib.import_module("AlarmDetection.DataProcessing.TaperShape")
    taper_grading = importlib.import_module("AlarmDetection.Grading.alarm_taper_shape")
    loose_grading = importlib.import_module("AlarmDetection.Grading.alarm_loose_coil")
    flat_result = importlib.import_module("AlarmDetection.Result.FlatRollData")
    alarm_result = importlib.import_module("AlarmDetection.Result.AlarmData")
    from Base.property.Types import DetectionTaperShapeType
    monkeypatch.setattr(taper_module.Globs.control, "taper_shape_type", DetectionTaperShapeType.LINE_TYPE)
    monkeypatch.setattr(alarmConfigProperty, "config", {
        "FlatRoll": {"Base": {"min": 35, "max": 45}},
        "TaperShape": {"Base": {"height": [10, 20], "angles": [0, 90]}},
        "LooseCoil": {"Base": {"width": 3}},
    })
    monkeypatch.setattr(config, "defectClassesProperty", SimpleNamespace(
        data={"visible": {"level": 4, "show": True}}, default={"show": True}))
    summary, taper_rows, loose_rows, flat_rows = [], [], [], []
    monkeypatch.setattr("CoilDataBase.Coil.add_obj", summary.append)
    monkeypatch.setattr(taper_grading, "add_obj", taper_rows.append)
    monkeypatch.setattr(loose_grading, "addAlarmLooseCoil", loose_rows.append)
    monkeypatch.setattr(flat_result, "addAlarmFlatRoll", flat_rows.append)
    monkeypatch.setattr(alarm_result.Alarm, "addObj", lambda rows: None)
    first, second = _integration("S"), _integration("L")
    second.npy_data[64, 92:97] = 0
    second.npy_data[64, 107:117] = 150
    second.defect_dict = {"visible": [(20, 20, 25, 25, 0, 0.9)]}
    errors = pipeline.detection_all([first, second])
    assert errors == {}
    assert len(summary) == len(taper_rows) == len(loose_rows) == len(flat_rows) == 2
    assert summary[0].grad == 1
    assert summary[1].taperShapeGrad == 3
    assert summary[1].looseCoilGrad == 3
    assert summary[1].flatRollGrad == 1
    assert summary[1].defectGrad == 4
    assert summary[1].grad == 4
    assert loose_rows[1].max_width == pytest.approx(5)
    assert taper_rows[1].out_taper_max_value == pytest.approx(25)
    assert set(second.alarmData.lineDataDict) == {0, 90}
    assert flat_rows[1].level == summary[1].flatRollGrad
    assert flat_rows[1].err_msg == summary[1].flatRollMsg
    detail = json.loads(flat_rows[1].data)
    assert detail["inner_diameter_mm"] == pytest.approx(second.alarmData.flatRollData.inner_diameter_mm())


def test_flat_detail_persists_calibrated_diameter_angle_and_grade():
    from AlarmDetection.Result.GradResult import AlarmGradResult
    data = _integration("S")
    data.scan3dCoordinateScaleX = 2
    data.accuracy_x = 2
    outer, inner = get_data(data.npy_mask)
    inner.ellipse.width = 20
    inner.ellipse.height = 40
    inner.ellipse.rotation_angle = 90
    data.alarmData.flatRollData = FlatRollData(data, inner, outer)
    data.alarmData.flat_roll_grad_result = AlarmGradResult(3, "规则内径过小", "")
    record = data.alarmData.flatRollData.get_alarm_flat_roll()
    detail = json.loads(record.data)
    assert detail["inner_diameter_mm"] == pytest.approx(20)
    assert detail["inner_ellipse_angle"] == 90
    assert record.inner_circle_width == 20  # Legacy raw-pixel contract is retained.
    assert record.accuracy_x == 2
    assert record.level == 3
    assert record.err_msg == "规则内径过小"


def test_flat_detail_commit_failure_returns_error_and_continues_other_models(monkeypatch):
    module = importlib.import_module("AlarmDetection.Result.AlarmData")
    saved = []
    monkeypatch.setattr(module.Alarm, "addObj", saved.append)
    monkeypatch.setattr(module, "should_store_model_name", lambda name: name == "PointData")
    data = _integration("S")

    def fail_commit():
        raise RuntimeError("flat database unavailable")

    data.alarmData.flatRollData = SimpleNamespace(commit=fail_commit)
    data.alarmData.lineDataDict = {0: SimpleNamespace(all_point_data_model=lambda data: ["point"])}
    errors = data.alarmData.commit()
    assert errors == {"S": ["flat_roll_commit: flat database unavailable"]}
    assert saved == [["point"]]


def test_summary_commit_failure_returns_surface_error_and_continues(monkeypatch):
    from AlarmDetection.Result.GradResult import AlarmGradResult
    module = importlib.import_module("AlarmDetection.Grading.CoilGrading")
    for name in ("grading_alarm_flat_roll", "grading_alarm_taper_shape", "grading_alarm_loose_coil", "grading_alarm_defects"):
        monkeypatch.setattr(module, name, lambda data: AlarmGradResult(1, "正常", ""))
    saved = []

    def commit_summary(row):
        if row.surface == "S":
            raise RuntimeError("summary database unavailable")
        saved.append(row)

    monkeypatch.setattr("CoilDataBase.Coil.add_obj", commit_summary)
    first, second = _integration("S"), _integration("L")
    first.alarmData.commit = lambda: {}
    second.alarmData.commit = lambda: {}
    errors = module.grading_all([first, second])
    assert errors == {"S": ["alarm_info_commit: summary database unavailable"]}
    assert [row.surface for row in saved] == ["L"]


def test_missing_eye_failure_survives_detector_and_grading(monkeypatch):
    module = importlib.import_module("AlarmDetection.DataProcessing.AlarmFlatRoll")
    from AlarmDetection.Grading.alarm_flat_roll import grading_alarm_flat_roll
    data = _integration("S")
    data.npy_mask.fill(0)
    module._detectionAlarmFlatRollAll_([data])
    result = grading_alarm_flat_roll(data)
    assert result.grad == 3
    assert data.alarm_processing_errors == ["flat_roll: outer circle contour is missing"]
