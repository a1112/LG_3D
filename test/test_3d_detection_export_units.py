"""Exercise the export boundary with persisted and legacy 3D measurements."""
import json
from types import SimpleNamespace

import pytest

from Base.utils.export.export_database import get_alarm_info


def _export(record):
    return get_alarm_info(SimpleNamespace(childrenAlarmFlatRoll=[record]), {"S": None, "L": None})


def _record(**changes):
    fields = dict(surface="S", inner_circle_width=2000, out_circle_width=4000,
                  accuracy_x=0.5, data=None)
    fields.update(changes)
    return SimpleNamespace(**fields)


@pytest.mark.parametrize("detail", [
    {"inner_diameter_mm": 700.25, "inner_ellipse_angle": 90},
    json.dumps({"inner_diameter_mm": 700.25, "inner_ellipse_angle": 90}),
])
def test_export_prefers_persisted_calibrated_inner_diameter(detail):
    values = _export(_record(data=detail))
    assert values["S端 检测内径"] == 700.25
    assert values["S端 检测外径"] == 2000


@pytest.mark.parametrize("detail", [None, "", "broken-json", "null", "[]", "{}"])
def test_legacy_export_uses_record_calibration_for_both_diameters(detail):
    values = _export(_record(data=detail))
    assert values["S端 检测内径"] == 1000
    assert values["S端 检测外径"] == 2000


@pytest.mark.parametrize("invalid", [float("nan"), float("inf"), -float("inf"), -1, 0, "bad"])
def test_invalid_persisted_inner_diameter_falls_back_to_record_calibration(invalid):
    values = _export(_record(data=json.dumps({"inner_diameter_mm": invalid})))
    assert values["S端 检测内径"] == 1000


def test_missing_legacy_calibration_retains_historical_export_scale():
    values = _export(_record(accuracy_x=None))
    assert values["S端 检测内径"] == pytest.approx(2000 * 0.3415023386478424)
    assert values["S端 检测外径"] == pytest.approx(4000 * 0.3415023386478424)


@pytest.mark.parametrize("invalid", [float("nan"), float("inf"), 0, -1, "bad"])
def test_present_invalid_calibration_is_not_replaced_by_a_different_calibration(invalid):
    values = _export(_record(accuracy_x=invalid))
    assert values["S端 检测内径"] == ""
    assert values["S端 检测外径"] == ""


def test_persisted_inner_diameter_is_usable_when_legacy_calibration_is_invalid():
    values = _export(_record(accuracy_x=float("nan"), data={"inner_diameter_mm": 701}))
    assert values["S端 检测内径"] == 701
    assert values["S端 检测外径"] == ""
