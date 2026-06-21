import sys
from pathlib import Path


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
