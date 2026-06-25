import sys
import json
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
for path in (
        ROOT / "app",
        ROOT / "app" / "Base",
        ROOT / "app" / "algorithm_runtime",
        ROOT / "package" / "CoilDataBase",
):
    path_text = str(path)
    if path_text not in sys.path:
        sys.path.insert(0, path_text)


def test_data_integration_bd_xyz_uses_distinct_y_scale(tmp_path):
    from Base.property.Base import DataIntegration

    data_integration = DataIntegration(123, str(tmp_path), "D", "S")
    data_integration.scan3dCoordinateScaleX = 0.5
    data_integration.scan3dCoordinateScaleY = 2.0
    data_integration.scan3dCoordinateScaleZ = 0.016

    assert data_integration.get_bd_xyz() == [0.5, 2.0, 0.016]


def test_coil_line_data_alarm_loose_coil_stores_width_in_mm():
    from Base.property.Base import CoilLineData

    line_data = CoilLineData()
    line_data.dataIntegration = SimpleNamespace(
        coilId=123,
        key="S",
        scan3dCoordinateScaleX=0.5,
        scan3dCoordinateScaleY=1.0,
    )
    line_data.rotation_angle = 0
    line_data.max_width = 739
    line_data.max_width_mm = 369.5
    line_data.data = {}

    alarm = line_data.get_alarm_loose_coil()

    assert alarm.max_width == 369.5
    detail = json.loads(alarm.data)
    assert detail["max_width_px"] == 739
    assert detail["max_width_mm"] == 369.5
    assert detail["max_width_unit"] == "mm"


def test_coil_line_data_detection_uses_x_scale_for_loose_width():
    from Base.property.Base import CoilLineData

    line_data = CoilLineData()
    line_data.dataIntegration = SimpleNamespace(
        scan3dCoordinateScaleX=0.5,
        scan3dCoordinateScaleY=1.0,
    )
    line_data.linePoint = [0, 800]
    line_data.lineData = [-301] * 739 + [0] * 61

    line_data.detection()

    assert line_data.max_width == 739
    assert line_data.max_width_mm == 369.5
    assert line_data.data["max_width_scale"] == 0.5
    assert line_data.data["max_width_scale_axis"] == "x"
