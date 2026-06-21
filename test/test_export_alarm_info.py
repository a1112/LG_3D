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


def _taper_alarm(surface):
    return SimpleNamespace(
        surface=surface,
        rotation_angle=40.0,
        out_taper_max_value=80.0,
        out_taper_min_value=-2.5,
        in_taper_max_value=75.0,
        in_taper_min_value=-10.0,
    )


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
