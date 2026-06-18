import sys
from pathlib import Path


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
