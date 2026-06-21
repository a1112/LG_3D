import sys
from pathlib import Path
from types import SimpleNamespace


PROJECT_ROOT = Path(__file__).resolve().parents[1]
COIL_DB_PATH = PROJECT_ROOT / "package" / "CoilDataBase"
path_text = str(COIL_DB_PATH)
if path_text not in sys.path:
    sys.path.insert(0, path_text)


def test_coil_summary_json_exposes_max_defect_status_fields():
    from CoilDataBase.models.CoilSummary import CoilSummary

    summary = CoilSummary()
    summary.Id = 123
    summary.CoilNo = "coil-123"
    summary.HasCoil = True
    summary.DefectCountS = 2
    summary.DefectCountL = 1
    summary.MaxDefectName = "scratch"
    summary.MaxDefectLevel = 4
    summary.MaxDefectSurface = "L"

    data = summary.get_json()

    assert data["DefectCountS"] == 2
    assert data["DefectCountL"] == 1
    assert data["maxDefectName"] == "scratch"
    assert data["maxDefectLevel"] == 4
    assert data["maxDefectSurface"] == "L"
    assert data["childrenCoilDefect"][0]["surface"] == "L"


def test_coil_summary_json_fields_select_visible_highest_defect(monkeypatch):
    from CoilDataBase import CoilSummary as coil_summary

    monkeypatch.setattr(
        coil_summary,
        "_load_defect_class_config",
        lambda: ({
            "scratch": {
                "level": 2,
                "show": True,
            },
            "dent": {
                "level": 4,
                "show": True,
            },
            "hidden": {
                "level": 5,
                "show": False,
            },
        }, True),
    )
    defects = [
        SimpleNamespace(defectName="scratch", surface="S"),
        SimpleNamespace(defectName="hidden", surface="L"),
        SimpleNamespace(defectName="dent", surface="L"),
    ]
    item_data = {}

    coil_summary._apply_max_defect_json_fields(item_data, defects)

    assert item_data["maxDefectName"] == "dent"
    assert item_data["maxDefectLevel"] == 4
    assert item_data["maxDefectSurface"] == "L"


def test_coil_summary_json_fields_clear_when_all_defects_hidden(monkeypatch):
    from CoilDataBase import CoilSummary as coil_summary

    monkeypatch.setattr(
        coil_summary,
        "_load_defect_class_config",
        lambda: ({
            "hidden": {
                "level": 5,
                "show": False,
            },
        }, True),
    )
    item_data = {"maxDefectName": "old", "maxDefectLevel": 4, "maxDefectSurface": "S"}

    coil_summary._apply_max_defect_json_fields(
        item_data, [SimpleNamespace(defectName="hidden", surface="L")])

    assert item_data["maxDefectName"] == ""
    assert item_data["maxDefectLevel"] == 0
    assert item_data["maxDefectSurface"] == ""
