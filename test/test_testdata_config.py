import sys
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "app" / "Server"))

from testdata_config import get_testdata_asset_dir, get_testdata_coil_id, get_testdata_coil_info, infer_surface_key  # noqa: E402


def test_testdata_coil_id_defaults_to_new_raw_dataset_id(monkeypatch):
    monkeypatch.delenv("API_TESTDATA_COIL_ID", raising=False)

    assert get_testdata_coil_id() == "193113"


def test_infer_surface_key_from_save_folder_path():
    assert infer_surface_key(r"D:\Save_S\193113\jpg\GRAY.jpg") == "S"
    assert infer_surface_key(r"E:\Save_L\193113\jpg\GRAY.jpg") == "L"


def test_surface_asset_dir_prefers_surface_subfolder(monkeypatch, tmp_path):
    testdata_dir = tmp_path / "193113"
    (testdata_dir / "S").mkdir(parents=True)
    monkeypatch.setenv("API_TESTDATA_DIR", str(testdata_dir))

    assert get_testdata_asset_dir(r"D:\Save_S\193113\jpg\GRAY.jpg") == testdata_dir / "S"


def test_testdata_coil_info_includes_render_state(monkeypatch, tmp_path):
    surface_dir = tmp_path / "193113" / "S"
    surface_dir.mkdir(parents=True)
    np.savez_compressed(surface_dir / "3D.npz", array=np.array([[0, 10], [20, 30]], dtype=np.float32))
    monkeypatch.setenv("API_TESTDATA_DIR", str(tmp_path / "193113"))

    info = get_testdata_coil_info("S")

    assert info["surface"] == "S"
    assert info["width"] == 2
    assert info["height"] == 2
    assert info["median_3d"] == 20
    assert info["median_3d_mm"] > 0
    assert "circleConfig" in info
