import importlib.util
import json
import logging
import subprocess
import sys
from pathlib import Path
from queue import Queue
from threading import Event, Lock
from types import ModuleType, SimpleNamespace

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def saver_module(monkeypatch):
    config = ModuleType("Base.CONFIG")
    config.serverConfigProperty = SimpleNamespace(balsam_exe="missing-balsam")
    log = ModuleType("Base.utils.Log")
    log.logger = logging.getLogger("test.save3d")
    globs = ModuleType("Globs")
    globs.control = SimpleNamespace(downsampleSize=1, median_filter_size=1,
                                    D3SaverWorkNum=1, D3SaverThreadMaxsize=2,
                                    D3SaverThreadType="threading", save_3d_obj=True)
    for name, module in (("Base.CONFIG", config), ("Base.utils.Log", log), ("Globs", globs)):
        monkeypatch.setitem(sys.modules, name, module)
    spec = importlib.util.spec_from_file_location("test_save3d_runtime", ROOT / "app/algorithm_runtime/Save3D/save.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def job(depth, *, mask=None, center=(0, 0), precision=(1, 1, 1), baseline=1000, offset=None, output="3D.obj"):
    if mask is None:
        mask = np.ones(depth.shape, dtype=np.uint8)
    result = ["coil", depth, mask, {}, {"inner_circle": {"ellipse": [center]}}, output, baseline, precision]
    if offset is not None:
        result.append(offset)
    return result


def test_point_cloud_uses_columns_for_x_rows_for_y_and_original_sampling(saver_module):
    saver_module.Globs.control.downsampleSize = 2
    depth = np.full((5, 7), 1000.0)
    result, _ = saver_module._get_point_cloud_(job(depth, center=(3, 1), precision=(2, 3, .5),
                                                baseline=900, offset=400), None)
    np.testing.assert_allclose(result["x_coords"], np.tile([-6, -2, 2, 6], (3, 1)))
    np.testing.assert_allclose(result["y_coords"], np.tile([[-3], [3], [9]], (1, 4)))
    np.testing.assert_allclose(result["z_coords"], 0, atol=1e-12)
    np.testing.assert_allclose(result["point_cloud"], np.stack([result[key] for key in
                               ("x_coords", "y_coords", "z_coords")], axis=-1)[result["valid_mask"]])


def test_point_cloud_does_not_mutate_sensor_data_or_revive_invalid_values(saver_module):
    depth = np.array([[0., -1., np.nan], [1000., np.inf, 1000.], [1000., 3000., 1000.]])
    original = depth.copy()
    result, _ = saver_module._get_point_cloud_(job(depth), None)
    np.testing.assert_array_equal(depth, original)
    assert result["point_cloud"].shape == (4, 3)
    assert np.isfinite(result["point_cloud"]).all()
    np.testing.assert_allclose(result["point_cloud"][:, 2], 0)


def test_downsampling_preserves_hole_and_flat_boundary(saver_module):
    depth = np.full((9, 9), 1000.)
    mask = np.ones((9, 9), dtype=bool)
    mask[3:6, 3:6] = False
    depth[~mask] = 0
    sampled, valid = saver_module._downsample_depth(depth, mask, 2, 5)
    assert not valid[2, 2]
    np.testing.assert_allclose(sampled[valid], 1000., atol=1e-10)


def test_unsampled_hole_prevents_triangle_bridge(saver_module):
    depth = np.full((7, 7), 1000.)
    depth[1, 1] = 0
    saver_module.Globs.control.downsampleSize = 2
    result, _ = saver_module._get_point_cloud_(job(depth), None)
    assert result["valid_mask"].all()
    assert not result["cell_valid_mask"][0, 0]
    mesh, vertices = saver_module.generate_mesh_from_grid(
        result["x_coords"], result["y_coords"], result["z_coords"], result["valid_mask"],
        cell_valid_mask=result["cell_valid_mask"])
    triangles = vertices[np.asarray(mesh.triangles)]
    assert len(triangles) == 16
    assert not np.any(np.all((triangles[:, :, 0] <= 2) & (triangles[:, :, 1] <= 2), axis=1))


def test_grid_discards_nan_and_degenerate_faces_without_mutating_mask(saver_module):
    x, y = np.meshgrid(np.arange(3), np.arange(3))
    z = np.zeros((3, 3))
    z[0, 0] = np.nan
    mask = np.ones((3, 3), dtype=bool)
    mesh, vertices = saver_module.generate_mesh_from_grid(x, y, z, mask)
    assert mask.all()
    assert np.isfinite(vertices).all()
    assert np.all(np.asarray(mesh.vertex_normals)[:, 2] > 0)
    with pytest.raises(ValueError, match="no valid surface triangles"):
        saver_module.generate_mesh_from_grid(np.zeros((2, 2)), np.zeros((2, 2)), np.zeros((2, 2)),
                                              np.ones((2, 2), dtype=bool))


def test_depth_discontinuity_does_not_produce_faces(saver_module):
    x, y = np.meshgrid(np.arange(2), np.arange(2))
    with pytest.raises(ValueError, match="no valid surface triangles"):
        saver_module.generate_mesh_from_grid(x, y, np.array([[0, 1000], [0, 1000]]), np.ones((2, 2)))


@pytest.mark.parametrize("step", [1, 2, 7, 10])
def test_gaussian_kernel_supports_configured_downsample_steps(saver_module, step):
    kernel = saver_module.gaussian_kernel(step)
    assert kernel.shape == (step, step)
    assert kernel.sum() == pytest.approx(1)
    np.testing.assert_allclose(kernel, kernel[::-1, ::-1])


@pytest.mark.parametrize("precision", [(0, 1, 1), (1, np.nan, 1), (1, 1), (1, 1, np.inf)])
def test_invalid_calibration_is_rejected(saver_module, precision):
    with pytest.raises(ValueError):
        saver_module._get_point_cloud_(job(np.ones((3, 3)), precision=precision), None)


def test_empty_depth_returns_empty_cloud(saver_module):
    result, _ = saver_module._get_point_cloud_(job(np.zeros((3, 4))), None)
    assert result["point_cloud"].shape == (0, 3)
    assert not result["valid_mask"].any()


def plane_mesh(module):
    x, y = np.meshgrid(np.arange(3), np.arange(3))
    return module.generate_mesh_from_grid(x, y, np.zeros((3, 3)), np.ones((3, 3), dtype=bool))[0]


def test_obj_round_trip_is_finite_and_has_local_faces(saver_module, tmp_path):
    mesh = plane_mesh(saver_module)
    output = tmp_path / "new" / "3D.obj"
    assert saver_module.save_colored_obj(mesh, None, output)
    loaded = saver_module.o3d.io.read_triangle_mesh(str(output))
    np.testing.assert_allclose(np.unique(np.asarray(loaded.vertices), axis=0),
                               np.unique(np.asarray(mesh.vertices), axis=0))
    assert len(loaded.triangles) == 8
    assert not list(output.parent.glob(".3D-*"))


def test_failed_obj_write_keeps_existing_model(saver_module, tmp_path, monkeypatch):
    output = tmp_path / "3D.obj"
    output.write_text("previous complete model")
    def failed_write(filename, *args, **kwargs):
        Path(filename).write_text("partial replacement")
        return False
    monkeypatch.setattr(saver_module.o3d.io, "write_triangle_mesh", failed_write)
    assert not saver_module.save_colored_obj(plane_mesh(saver_module), None, output)
    assert output.read_text() == "previous complete model"
    assert sorted(path.name for path in tmp_path.iterdir()) == ["3D.obj"]


def test_color_export_does_not_modify_input_colors(saver_module, tmp_path):
    mesh = plane_mesh(saver_module)
    colors = np.full((9, 4), 255.)
    assert saver_module.save_colored_obj(mesh, colors, tmp_path / "color.obj")
    np.testing.assert_allclose(colors, 255.)
    np.testing.assert_allclose(np.asarray(mesh.vertex_colors), 1.)


@pytest.mark.parametrize("outcome", ["ok", "nonzero", "timeout", "missing"])
def test_balsam_reports_actual_result(saver_module, tmp_path, monkeypatch, outcome):
    output = tmp_path / "3D.obj"
    output.write_text("obj")
    monkeypatch.setattr(saver_module.shutil, "which", lambda value: None if outcome == "missing" else "balsam.exe")
    def run(command, **kwargs):
        assert Path(command[-1]).is_absolute()
        assert kwargs["timeout"] > 0
        if outcome == "timeout":
            raise subprocess.TimeoutExpired(command, kwargs["timeout"])
        return SimpleNamespace(returncode=0 if outcome == "ok" else 2, stderr="error")
    monkeypatch.setattr(saver_module.subprocess, "run", run)
    assert saver_module.toMesh(output) is (outcome == "ok")


def test_full_job_writes_calibrated_obj_without_balsam(saver_module, tmp_path, monkeypatch):
    monkeypatch.setattr(saver_module.shutil, "which", lambda value: None)
    output = tmp_path / "3D.obj"
    saver_module._save_3d(job(np.full((4, 4), 5000.), precision=(.2, .4, .1),
                             baseline=1750, offset=1250, output=output), None)
    loaded = saver_module.o3d.io.read_triangle_mesh(str(output))
    vertices = np.asarray(loaded.vertices)
    status = json.loads((tmp_path / "mesh_status.json").read_text(encoding="utf-8"))
    assert status["state"] == "ready"
    assert status["optimizer_success"] is False
    assert status["coil_id"] == "coil"
    assert len(loaded.triangles) == 18
    np.testing.assert_allclose(np.ptp(vertices, axis=0), [.6, 1.2, 0], atol=1e-8)


def test_saver_drains_and_rejects_jobs_after_shutdown(saver_module, monkeypatch):
    saved = []
    monkeypatch.setattr(saver_module, "_save_3d", lambda data, manager: saved.append(data))
    saver = saver_module.D3Saver(None, None)
    assert saver.add_("first")
    assert saver.add_("second")
    saver.join()
    saver.join()
    assert not saver.add_("third")
    assert saved == ["first", "second"]
    assert not any(worker.is_alive() for worker in saver.processes)


def test_worker_failure_does_not_block_following_jobs(saver_module, monkeypatch):
    saved = []
    def save(data, manager):
        if data == "bad":
            raise ValueError("broken job")
        saved.append(data)
    monkeypatch.setattr(saver_module, "_save_3d", save)
    saver = saver_module.D3Saver(None, None)
    saver.add_("bad")
    saver.add_("good")
    saver.join()
    assert saved == ["good"]
    assert saver.queue.unfinished_tasks == 0


@pytest.mark.parametrize("value", ["NaN", "inf", "bad"])
def test_timeout_config_rejects_nonfinite_values(saver_module, monkeypatch, value):
    monkeypatch.setenv("LG3D_BALSAM_TIMEOUT", value)
    assert saver_module._get_balsam_timeout() == saver_module.DEFAULT_BALSAM_TIMEOUT


def test_failed_job_publishes_error_and_preserves_previous_obj(saver_module, tmp_path):
    output = tmp_path / "3D.obj"
    output.write_text("previous mesh")
    assert saver_module._save_3d(job(np.zeros((4, 4)), output=output), None) is False
    status = json.loads((tmp_path / "mesh_status.json").read_text(encoding="utf-8"))
    assert status["state"] == "error"
    assert "not enough valid depth" in status["error"]
    assert output.read_text() == "previous mesh"
    assert not list(tmp_path.glob(".mesh_status-*"))


def test_failed_writer_does_not_start_optimizer(saver_module, tmp_path, monkeypatch):
    monkeypatch.setattr(saver_module, "save_colored_obj", lambda *args: False)
    def forbidden_optimizer(*args):
        pytest.fail("optimizer started after failed OBJ save")
    monkeypatch.setattr(saver_module, "toMesh", forbidden_optimizer)
    output = tmp_path / "3D.obj"
    assert saver_module._save_3d(job(np.full((4, 4), 1000.), output=output), None) is False
    status = json.loads((tmp_path / "mesh_status.json").read_text(encoding="utf-8"))
    assert status["state"] == "error"
    assert "Open3D" in status["error"]


def test_timed_out_thread_pool_exits_after_draining_without_sentinel(saver_module, monkeypatch):
    first_started = Event()
    release_first = Event()
    saved = []
    def save(data, manager):
        if data == "first":
            first_started.set()
            release_first.wait(timeout=2)
        saved.append(data)
    monkeypatch.setattr(saver_module, "_save_3d", save)
    saver_module.Globs.control.D3SaverThreadMaxsize = 1
    saver = saver_module.D3Saver(None, None)
    saver.join_timeout = 0.01
    saver.queue_put_timeout = 0.01
    try:
        assert saver.add_("first")
        assert first_started.wait(timeout=1)
        assert saver.add_("second")
        saver.join()
        assert not saver.add_("third")
    finally:
        release_first.set()
        for worker in saver.processes:
            worker.join(timeout=2)
    assert saved == ["first", "second"]
    assert not any(worker.is_alive() for worker in saver.processes)


@pytest.mark.parametrize("failure", ["full", "closed", "error"])
def test_rejected_rebuild_marks_error_without_losing_previous_model(saver_module, tmp_path, monkeypatch, failure):
    output = tmp_path / "3D.obj"
    output.write_text("previous complete model")
    saver_module._write_mesh_status(output, "coil", "ready", optimizer_success=True)
    saver = saver_module.D3Saver.__new__(saver_module.D3Saver)
    saver._state_lock = Lock()
    saver._joined = failure == "closed"
    saver.queue_put_timeout = 0.01
    saver.queue = Queue(maxsize=1)
    if failure == "full":
        saver.queue.put_nowait("occupied")
    elif failure == "error":
        def failed_put(*args, **kwargs):
            raise OSError("queue handle closed")
        monkeypatch.setattr(saver.queue, "put", failed_put)
    assert saver.add_(job(np.full((4, 4), 1000.), output=output)) is False
    status = json.loads((tmp_path / "mesh_status.json").read_text(encoding="utf-8"))
    assert status["state"] == "error"
    assert "3D mesh rebuild" in status["error"]
    assert status["optimizer_success"] is None
    assert output.read_text() == "previous complete model"
