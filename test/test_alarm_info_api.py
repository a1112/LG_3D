import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
for path in (
        ROOT / "app",
        ROOT / "app" / "Server",
        ROOT / "app" / "Base",
        ROOT / "app" / "algorithm_runtime",
        ROOT / "package" / "CoilDataBase",
):
    path_text = str(path)
    if path_text not in sys.path:
        sys.path.insert(0, path_text)


def test_normalize_loose_alarm_converts_legacy_pixel_width():
    from AlarmDetection.Server.ApiAlarmInfo import _normalize_loose_alarm_dict

    alarm_data = {
        "surface": "S",
        "max_width": 739,
        "data": "",
    }

    result = _normalize_loose_alarm_dict(alarm_data, surface_scale=0.33693358302116394)
    detail = json.loads(result["data"])

    assert result["max_width"] == pytest.approx(739 * 0.33693358302116394)
    assert detail["max_width_px"] == 739
    assert detail["max_width_mm"] == pytest.approx(739 * 0.33693358302116394)
    assert detail["max_width_unit"] == "mm"
    assert detail["max_width_scale_axis"] == "x"


def test_normalize_loose_alarm_keeps_valid_mm_width():
    from AlarmDetection.Server.ApiAlarmInfo import _normalize_loose_alarm_dict

    alarm_data = {
        "surface": "S",
        "max_width": 18.5,
        "data": json.dumps({
            "max_width_mm": 18.5,
            "max_width_unit": "mm",
        }),
    }

    result = _normalize_loose_alarm_dict(alarm_data, surface_scale=0.33693358302116394)
    detail = json.loads(result["data"])

    assert result["max_width"] == 18.5
    assert detail["max_width_mm"] == 18.5


def test_normalize_loose_alarm_repairs_mislabeled_pixel_detail():
    from AlarmDetection.Server.ApiAlarmInfo import _normalize_loose_alarm_dict

    alarm_data = {
        "surface": "S",
        "max_width": 739,
        "data": json.dumps({
            "max_width_px": 739,
            "max_width_mm": 739,
            "max_width_unit": "mm",
        }),
    }

    result = _normalize_loose_alarm_dict(alarm_data, surface_scale=0.33693358302116394)

    assert result["max_width"] == pytest.approx(739 * 0.33693358302116394)
