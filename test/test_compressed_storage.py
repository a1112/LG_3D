import sys
from pathlib import Path

import numpy as np
from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "app"))
sys.path.insert(0, str(PROJECT_ROOT / "package" / "CoilDataBase"))

from Base.property.ServerConfigProperty import SurfaceConfigProperty  # noqa: E402
from Base.tools.compressed_storage import (  # noqa: E402
    compressed_image_path,
    compressed_numpy_path,
    save_compressed_image,
    save_compressed_numpy,
)


def test_compressed_image_path_replaces_bmp_with_jpg():
    assert compressed_image_path(Path("coil/2d/0.bmp")) == Path("coil/2d/0.jpg")
    assert compressed_image_path(Path("coil/2d/0.jpg")) == Path("coil/2d/0.jpg")


def test_compressed_numpy_path_replaces_npy_with_npz():
    assert compressed_numpy_path(Path("coil/3d/0.npy")) == Path("coil/3d/0.npz")
    assert compressed_numpy_path(Path("coil/3d/0.npz")) == Path("coil/3d/0.npz")


def test_save_compressed_image_writes_jpg_and_not_bmp(tmp_path):
    source_path = tmp_path / "coil" / "2d" / "0.bmp"
    image = Image.fromarray(np.full((8, 8), 127, dtype=np.uint8))

    output_path = save_compressed_image(image, source_path)

    assert output_path == source_path.with_suffix(".jpg")
    assert output_path.exists()
    assert not source_path.exists()
    with Image.open(output_path) as saved:
        assert saved.size == (8, 8)


def test_save_compressed_numpy_writes_npz_and_not_npy(tmp_path):
    source_path = tmp_path / "coil" / "3d" / "0.npy"
    array = np.arange(12, dtype=np.uint16).reshape(3, 4)

    output_path = save_compressed_numpy(array, source_path)

    assert output_path == source_path.with_suffix(".npz")
    assert output_path.exists()
    assert not source_path.exists()
    with np.load(output_path) as data:
        assert np.array_equal(data["array"], array)


def test_surface_config_uses_npz_as_default_3d_path():
    config = SurfaceConfigProperty(
        {
            "key": "S",
            "saveFolder": "D:/data/S",
            "rotate": 0,
            "x_rotate": 0,
            "direction": "R",
            "folderList": [],
        }
    )

    assert Path(config.get_3d_file("193113")).name == "3D.npz"


def test_capture_save_code_does_not_write_bmp_or_npy_outputs():
    source = (PROJECT_ROOT / "app" / "CapTrue" / "ImageDataSave.py").read_text(encoding="utf-8")

    assert '.bmp"' not in source
    assert ".bmp'" not in source
    assert '.npy"' not in source
    assert ".npy'" not in source
