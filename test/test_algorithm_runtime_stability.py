import sys
from pathlib import Path
from types import SimpleNamespace


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = PROJECT_ROOT / "app"
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))


def test_legacy_capture_killer_is_opt_in():
    source = (PROJECT_ROOT / "app" / "algorithm_runtime" /
              "main.py").read_text(encoding="utf-8")

    assert 'os.getenv("LG3D_ENABLE_LEGACY_CAPTURE_LIS", "0") == "1"' in source
    assert source.index("LG3D_ENABLE_LEGACY_CAPTURE_LIS") < source.index(
        "import Lis")


def test_3d_camera_workers_share_one_area_model():
    source = (PROJECT_ROOT / "app" / "algorithm_runtime" /
              "SplicingService" / "DataFolder.py").read_text(encoding="utf-8")

    assert "def _get_shared_coil_area_model" in source
    assert "self.coilAreaModel = _get_shared_coil_area_model()" in source
    assert "self.coilAreaModel = CoilAreaModel()" not in source


def test_base_model_cleanup_releases_only_predictor_call_references():
    from app.Base.alg.model_memory import release_predictor_input_references

    weights = object()
    predictor = SimpleNamespace(
        dataset=object(),
        batch=object(),
        results=object(),
        plotted_img=object(),
        model=weights,
    )
    model = SimpleNamespace(predictor=predictor)

    release_predictor_input_references(model)

    assert predictor.dataset is None
    assert predictor.batch is None
    assert predictor.results is None
    assert predictor.plotted_img is None
    assert predictor.model is weights


def test_permanent_3d_workers_drop_completed_coil_payload_references():
    data_folder_source = (PROJECT_ROOT / "app" / "algorithm_runtime" /
                          "SplicingService" /
                          "DataFolder.py").read_text(encoding="utf-8")
    mosaic_source = (PROJECT_ROOT / "app" / "algorithm_runtime" /
                     "SplicingService" /
                     "ImageMosaic.py").read_text(encoding="utf-8")
    saver_source = (PROJECT_ROOT / "app" / "algorithm_runtime" /
                    "SplicingService" /
                    "ImageSaver.py").read_text(encoding="utf-8")
    mesh_saver_source = (PROJECT_ROOT / "app" / "algorithm_runtime" /
                         "Save3D" / "save.py").read_text(encoding="utf-8")

    assert "data3_d_full = None" in data_folder_source
    assert "data_integration = None" in mosaic_source
    assert "item = None" in saver_source
    assert "data = None" in mesh_saver_source
    assert "self.colorImageDict[name] = image" not in mosaic_source


def test_false_colour_rendering_avoids_full_size_temporary_copies():
    source = (PROJECT_ROOT / "app" / "algorithm_runtime" /
              "SplicingService" / "ImageMosaic.py").read_text(
                  encoding="utf-8")
    save_3d_source = source.split("async def save3_d", 1)[1].split(
        "def join_saver", 1)[0]

    assert "non_zero_elements = npy__[npy__ != 0]" not in save_3d_source
    assert "npy__.astype(np.float32, copy=True)" in save_3d_source
    assert "np.clip(depth_map_scaled" in save_3d_source
    assert "out=depth_map_scaled" in save_3d_source
