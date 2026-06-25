import json
import sys
from pathlib import Path
from types import SimpleNamespace


PROJECT_ROOT = Path(__file__).resolve().parents[1]
for path in (
        PROJECT_ROOT / "app",
        PROJECT_ROOT / "app" / "Server",
        PROJECT_ROOT / "package" / "CoilDataBase",
):
    path_text = str(path)
    if path_text not in sys.path:
        sys.path.insert(0, path_text)


def _export_config():
    from Base.utils.export.export_config import ExportConfig

    export_config = ExportConfig()
    export_config.export_header_data = False
    export_config.export_plc_data = False
    export_config.export_alarm_info = False
    export_config.export_taper_shape_info = True
    export_config.export_alarm_loose = False
    export_config.export_defect_data = False
    return export_config


def test_export_includes_taper_alarm_info_without_taper_detail():
    from Base.utils.export.export_database import get_item_data

    secondary_coil = SimpleNamespace(
        childrenAlarmInfo=[
            SimpleNamespace(
                surface="S",
                taperShapeGrad=3,
                taperShapeMsg="塔形检测失败: 无有效线数据",
            )
        ],
        childrenAlarmTaperShape=[],
    )

    item_data = get_item_data(secondary_coil, _export_config())

    assert 3 in item_data.values()
    assert "塔形检测失败: 无有效线数据" in item_data.values()


def test_export_includes_taper_worst_point_metadata():
    from Base.utils.export.export_database import get_item_data

    secondary_coil = SimpleNamespace(
        childrenAlarmInfo=[],
        childrenAlarmTaperShape=[
            SimpleNamespace(
                surface="S",
                rotation_angle=40.0,
                out_taper_max_value=80.0,
                out_taper_min_value=-2.5,
                in_taper_max_value=75.0,
                in_taper_min_value=-10.0,
                data=json.dumps({
                    "worst_label": "外塔最高值",
                    "worst_mm": 80.0,
                    "worst_abs_mm": 80.0,
                    "worst_point_type": "outer_max_point",
                    "worst_x": 10.0,
                    "worst_y": 20.0,
                    "worst_z": 260.0,
                    "worst_angle": 40.0,
                    "angle_filter": [270.0, 90.0],
                    "angle_tolerance": 0.5,
                    "valid_angle_coverage_ratio": 1.0,
                    "valid_line_count": 2,
                    "covered_angle_count": 2,
                    "taper_attempt_count": 2,
                    "raw_taper_attempt_count": 36,
                    "detection_error_count": 0,
                    "raw_detection_error_count": 1,
                    "warning_count": 1,
                    "grading_error_count": 0,
                }, ensure_ascii=False),
            )
        ],
    )

    item_data = get_item_data(secondary_coil, _export_config())

    assert item_data["S端 塔形最严重类型"] == "外塔最高值"
    assert item_data["S端 塔形最严重值"] == 80.0
    assert item_data["S端 塔形最严重绝对值"] == 80.0
    assert item_data["S端 塔形最严重点类型"] == "outer_max_point"
    assert item_data["S端 塔形最严重点X"] == 10.0
    assert item_data["S端 塔形最严重点Y"] == 20.0
    assert item_data["S端 塔形最严重点Z"] == 260.0
    assert item_data["S端 塔形最严重角度"] == 40.0
    assert item_data["S端 塔形判定角度"] == "270, 90"
    assert item_data["S端 塔形角度容差"] == 0.5
    assert item_data["S端 塔形有效角度覆盖率"] == 1.0
    assert item_data["S端 塔形有效线数量"] == 2
    assert item_data["S端 塔形覆盖角度数量"] == 2
    assert item_data["S端 塔形检测角度数量"] == 2
    assert item_data["S端 塔形原始检测角度数量"] == 36
    assert item_data["S端 塔形检测失败数量"] == 0
    assert item_data["S端 塔形原始检测失败数量"] == 1
    assert item_data["S端 塔形配置警告数量"] == 1
    assert item_data["S端 塔形分级无效线数量"] == 0


class _FakeWorksheet:
    def __init__(self):
        self.rows = []

    def write_row(self, row_num, col_num, row_data):
        self.rows.append(list(row_data))

    def add_table(self, *_args, **_kwargs):
        pass


class _FakeWorkbook:
    def __init__(self):
        self.worksheet = _FakeWorksheet()

    def add_worksheet(self, _name):
        return self.worksheet


def _taper_alarm(
    surface,
    *,
    level=1,
    rotation_angle=40.0,
    out_taper_max_value=80.0,
    worst_abs_mm=80.0,
    marker="outer_max_point",
):
    return SimpleNamespace(
        surface=surface,
        level=level,
        rotation_angle=rotation_angle,
        out_taper_max_value=out_taper_max_value,
        out_taper_min_value=-2.5,
        in_taper_max_value=75.0,
        in_taper_min_value=-10.0,
        data=json.dumps({
            "worst_abs_mm": worst_abs_mm,
            "worst_point_type": marker,
            "worst_angle": rotation_angle,
        }, ensure_ascii=False),
    )


def test_export_taper_info_uses_most_severe_alarm_for_same_surface():
    from Base.utils.export.export_database import get_item_data

    secondary_coil = SimpleNamespace(
        childrenAlarmInfo=[],
        childrenAlarmTaperShape=[
            _taper_alarm(
                "S",
                level=1,
                rotation_angle=10.0,
                out_taper_max_value=120.0,
                worst_abs_mm=120.0,
                marker="light_taper_alarm",
            ),
            _taper_alarm(
                "S",
                level=3,
                rotation_angle=40.0,
                out_taper_max_value=80.0,
                worst_abs_mm=80.0,
                marker="severe_taper_alarm",
            ),
        ],
    )

    item_data = get_item_data(secondary_coil, _export_config())
    values = set(item_data.values())

    assert "severe_taper_alarm" in values
    assert "light_taper_alarm" not in values


def test_export_info_data_uses_union_headers_for_surface_specific_taper_fields():
    from Base.utils.export.export_database import export_info_data

    workbook = _FakeWorkbook()
    export_info_data(
        [
            SimpleNamespace(childrenAlarmInfo=[], childrenAlarmTaperShape=[_taper_alarm("S")]),
            SimpleNamespace(childrenAlarmInfo=[], childrenAlarmTaperShape=[_taper_alarm("L")]),
        ],
        workbook,
        _export_config(),
    )

    headers = workbook.worksheet.rows[0]

    assert "S端 检测角度" in headers
    assert "L端 检测角度" in headers
