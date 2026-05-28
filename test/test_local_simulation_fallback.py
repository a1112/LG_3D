import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "app"))
sys.path.insert(0, str(PROJECT_ROOT / "app" / "Server"))
sys.path.insert(0, str(PROJECT_ROOT / "package" / "CoilDataBase"))

from api import ApiDataBase


def enable_test_mode(monkeypatch, available=True):
    monkeypatch.setattr(ApiDataBase.CONFIG, "developer_mode", True, raising=False)
    monkeypatch.setattr(ApiDataBase.CONFIG, "isLoc", True, raising=False)
    monkeypatch.setattr(ApiDataBase, "_testdata_available", lambda: available)


def disable_test_mode(monkeypatch):
    monkeypatch.setattr(ApiDataBase.CONFIG, "developer_mode", False, raising=False)
    monkeypatch.setattr(ApiDataBase.CONFIG, "isLoc", True, raising=False)
    monkeypatch.setattr(ApiDataBase, "_testdata_available", lambda: True)


def test_empty_summary_result_uses_testdata_coil_in_local_test_mode(monkeypatch):
    enable_test_mode(monkeypatch)

    result = ApiDataBase._with_test_mode_coil_fallback({"value": [], "Count": 0})

    assert result["Count"] == 1
    assert len(result["value"]) == 1
    coil = result["value"][0]
    assert coil["Id"] == 125143
    assert coil["CoilNo"] == "125143"
    assert coil["hasCoil"] is True
    assert coil["hasAlarmInfo"] is True
    assert set(coil["AlarmInfo"]) == {"S", "L"}


def test_empty_list_result_uses_testdata_coil_in_local_test_mode(monkeypatch):
    enable_test_mode(monkeypatch)

    result = ApiDataBase._with_test_mode_coil_fallback([])

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["Msg"] == "TestData/125143"


def test_non_empty_database_result_is_not_replaced(monkeypatch):
    enable_test_mode(monkeypatch)
    existing = {"value": [{"Id": 7, "CoilNo": "real"}], "Count": 1}

    result = ApiDataBase._with_test_mode_coil_fallback(existing)

    assert result is existing
    assert result["value"][0]["Id"] == 7


def test_fallback_is_disabled_outside_local_test_mode(monkeypatch):
    disable_test_mode(monkeypatch)
    empty_result = {"value": [], "Count": 0}

    result = ApiDataBase._with_test_mode_coil_fallback(empty_result)

    assert result is empty_result


def test_fallback_requires_testdata_assets(monkeypatch):
    enable_test_mode(monkeypatch, available=False)
    empty_result = {"value": [], "Count": 0}

    result = ApiDataBase._with_test_mode_coil_fallback(empty_result)

    assert result is empty_result


def test_testdata_coil_has_required_qml_alarm_shape(monkeypatch):
    enable_test_mode(monkeypatch)

    coil = ApiDataBase._test_mode_coil_item()

    for surface in ("S", "L"):
        alarm = coil["AlarmInfo"][surface]
        assert alarm["surface"] == surface
        assert "taperShapeGrad" in alarm
        assert "looseCoilGrad" in alarm
        assert "flatRollGrad" in alarm
    for key in ("CreateTime", "DetectionTime", "DateTime"):
        assert {"year", "month", "day", "hour", "minute", "second"} <= set(coil[key])
