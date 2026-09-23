from pathlib import Path
import json
import sys

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SERVER_ROOT = PROJECT_ROOT / "app" / "Server"
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from testdata_mesh import ensure_testdata_mesh, write_heightmap_obj  # noqa: E402


def test_write_heightmap_obj_creates_vertices_and_faces(tmp_path):
    npz_path = tmp_path / "3D.npz"
    obj_path = tmp_path / "meshes" / "defaultobject.obj"
    data = np.array([[0, 1000, 1001, 0], [1002, 1003, 1004, 1005],
                     [1006, 1007, 1008, 1009]],
                    dtype=np.float32)
    np.savez_compressed(npz_path, array=data)
    result = write_heightmap_obj(npz_path, obj_path, max_size=8)
    assert result == obj_path
    text = obj_path.read_text(encoding="ascii")
    assert "\nv " in "\n" + text
    assert "\nf " in "\n" + text
    assert "defaultobject.obj" in str(result)


def test_ensure_testdata_mesh_prefers_surface_npz(tmp_path, monkeypatch):
    monkeypatch.setenv("API_TESTDATA_DIR", str(tmp_path / "193113"))
    surface_dir = tmp_path / "193113" / "S"
    surface_dir.mkdir(parents=True)
    np.savez_compressed(surface_dir / "3D.npz",
                        array=np.ones((4, 4), dtype=np.float32) * 1200)
    mesh_path = ensure_testdata_mesh("S", "193113", max_size=8)
    assert mesh_path == surface_dir / "meshes" / "defaultobject.obj"
    assert mesh_path.exists()


def test_write_heightmap_obj_accepts_npy_and_data_scales(tmp_path):
    data_path = tmp_path / "3D.npy"
    np.save(data_path, np.ones((2, 2), dtype=np.float32))
    (tmp_path / "data.json").write_text(json.dumps({
        "scan3dCoordinateScaleX": 2,
        "scan3dCoordinateScaleY": 3,
        "scan3dCoordinateScaleZ": 4,
    }),
                                        encoding="utf-8")
    obj_path = tmp_path / "meshes" / "defaultobject.obj"
    assert write_heightmap_obj(data_path, obj_path).exists()
    vertices = [
        line for line in obj_path.read_text().splitlines()
        if line.startswith("v ")
    ]
    assert "v -1.000000 -1.500000 0.000000" in vertices


def test_write_heightmap_obj_preserves_hole_and_old_mesh_on_failure(tmp_path):
    data_path = tmp_path / "3D.npy"
    np.save(data_path, np.ones((3, 3), dtype=np.float32))
    obj_path = tmp_path / "meshes" / "defaultobject.obj"
    write_heightmap_obj(data_path, obj_path)
    original = obj_path.read_text()
    np.save(data_path,
            np.array([[1, 0, 1], [0, 0, 0], [1, 0, 1]], dtype=np.float32))
    try:
        write_heightmap_obj(data_path, obj_path)
    except ValueError:
        pass
    else:
        raise AssertionError(
            "disconnected heightmap should not produce a mesh")
    assert obj_path.read_text() == original


def test_mesh_rejects_empty_shape_and_invalid_max_size(tmp_path):
    data_path = tmp_path / "3D.npy"
    obj_path = tmp_path / "meshes" / "defaultobject.obj"
    np.save(data_path, np.empty((0, 3), dtype=np.float32))
    for max_size in (0, -1):
        try:
            write_heightmap_obj(data_path, obj_path, max_size=max_size)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid input should fail")


def test_mesh_handles_non_object_metadata_and_cache_inputs(
        tmp_path, monkeypatch):
    monkeypatch.setenv("API_TESTDATA_DIR", str(tmp_path / "193113"))
    surface_dir = tmp_path / "193113" / "S"
    surface_dir.mkdir(parents=True)
    np.save(surface_dir / "3D.npy", np.ones((8, 8), dtype=np.float32))
    metadata = surface_dir / "data.json"
    metadata.write_text("[]", encoding="utf-8")
    mesh_path = ensure_testdata_mesh("S", max_size=8)
    assert "max_size=8" in mesh_path.read_text(
        encoding="ascii").splitlines()[0]
    mesh_path = ensure_testdata_mesh("S", max_size=4)
    assert "max_size=4" in mesh_path.read_text(
        encoding="ascii").splitlines()[0]
    metadata.write_text(json.dumps({"scan3dCoordinateScaleX": 2}),
                        encoding="utf-8")
    metadata.touch()
    mesh_path = ensure_testdata_mesh("S", max_size=4)
    assert "-2.000000" in mesh_path.read_text(encoding="ascii")


def test_fine_source_hole_is_not_filled_by_downsampling(tmp_path):
    data_path = tmp_path / "3D.npy"
    data = np.ones((8, 8), dtype=np.float32)
    data[3, 3] = 0
    np.save(data_path, data)
    obj_path = tmp_path / "meshes" / "defaultobject.obj"
    write_heightmap_obj(data_path, obj_path, max_size=4)
    text = obj_path.read_text(encoding="ascii")
    assert sum(line.startswith("f ") for line in text.splitlines()) < 18
