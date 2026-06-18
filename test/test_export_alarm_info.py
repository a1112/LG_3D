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
