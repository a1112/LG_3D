from pathlib import Path
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
    data = np.array(
        [
            [0, 1000, 1001, 0],
            [1002, 1003, 1004, 1005],
            [1006, 1007, 1008, 1009],
        ],
        dtype=np.float32,
    )
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
    np.savez_compressed(surface_dir / "3D.npz", array=np.ones((4, 4), dtype=np.float32) * 1200)

    mesh_path = ensure_testdata_mesh("S", "193113", max_size=8)

    assert mesh_path == surface_dir / "meshes" / "defaultobject.obj"
    assert mesh_path.exists()
