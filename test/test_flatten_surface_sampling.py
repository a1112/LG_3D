import sys
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "app"))
sys.path.insert(0, str(PROJECT_ROOT / "package" / "CoilDataBase"))

from Base.tools import FlattenSurface  # noqa: E402


def test_flatten_surface_samples_plane_fit_points(monkeypatch):
    monkeypatch.setenv("ALGORITHM_3D_FLATTEN_SAMPLE_POINTS", "100")
    captured = {}

    def fake_fit_plane(x_values, y_values, z_values):
        captured["count"] = len(z_values)
        return 0.0, 0.0, 0.0, np.array([0.0, 0.0, -1.0])

    monkeypatch.setattr(FlattenSurface, "fit_plane", fake_fit_plane)
    data = np.full((120, 120), 2000, dtype=np.uint16)
    mask = np.ones_like(data, dtype=bool)

    FlattenSurface.flatten_surface_by_rotation(data, mask, media_z=2000)

    assert captured["count"] == 100


def test_fit_plane_estimates_plane_without_sklearn():
    x_values = np.array([0, 1, 0, 1, 2], dtype=float)
    y_values = np.array([0, 0, 1, 1, 2], dtype=float)
    z_values = 2 * x_values + 3 * y_values + 5

    a_value, b_value, c_value, normal = FlattenSurface.fit_plane(x_values, y_values, z_values)

    np.testing.assert_allclose([a_value, b_value, c_value], [2, 3, 5], rtol=1e-12, atol=1e-12)
    np.testing.assert_allclose(normal, np.array([2, 3, -1]), rtol=1e-12, atol=1e-12)
