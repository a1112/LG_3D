import json
import multiprocessing
import os
import shutil
import subprocess
import threading
import time
from datetime import datetime, timezone
from multiprocessing import JoinableQueue as MulQueue
from pathlib import Path
from tempfile import NamedTemporaryFile
from queue import Empty, Full, Queue as ThreadQueue

from matplotlib import colormaps
from matplotlib.colors import Normalize

import numpy as np
import open3d as o3d
from scipy.ndimage import convolve, median_filter, minimum_filter
from scipy.spatial import Delaunay, QhullError

from Base.CONFIG import serverConfigProperty
from Base.utils.Log import logger
import Globs


DEFAULT_D3_QUEUE_PUT_TIMEOUT = 5.0
DEFAULT_BALSAM_TIMEOUT = 300.0
DEFAULT_D3_JOIN_GRACE_SECONDS = 30.0


def _get_float_env(name: str, default: float) -> float:
    raw_value = os.getenv(name, str(default))
    try:
        value = float(raw_value)
        if not np.isfinite(value):
            raise ValueError("timeout must be finite")
        return max(value, 0.1)
    except ValueError:
        logger.warning("invalid %s=%s, use %s", name, raw_value, default)
        return default


def _get_d3_queue_put_timeout() -> float:
    return _get_float_env("LG3D_D3_SAVE_QUEUE_PUT_TIMEOUT", DEFAULT_D3_QUEUE_PUT_TIMEOUT)


def _get_balsam_timeout() -> float:
    return _get_float_env("LG3D_BALSAM_TIMEOUT", DEFAULT_BALSAM_TIMEOUT)


def _get_d3_join_timeout() -> float:
    default_timeout = _get_balsam_timeout() + DEFAULT_D3_JOIN_GRACE_SECONDS
    return _get_float_env("LG3D_D3_SAVE_JOIN_TIMEOUT", default_timeout)


def gaussian_kernel(size, sigma=1):
    """Return a normalized Gaussian kernel for depth downsampling."""
    try:
        size = int(size)
        sigma = float(sigma)
    except (TypeError, ValueError) as exc:
        raise ValueError("kernel size and sigma must be numeric") from exc
    if size < 1 or not np.isfinite(sigma) or sigma <= 0:
        raise ValueError("kernel size and sigma must be positive")
    coordinates = np.arange(size, dtype=np.float64) - (size - 1) / 2
    kernel_1d = np.exp(-0.5 * (coordinates / sigma)**2)
    kernel_1d /= kernel_1d.sum()
    kernel_2d = np.outer(kernel_1d, kernel_1d)
    return kernel_2d / kernel_2d.sum()


def downsample_data_with_convolution(matrix, kernel_size):
    """Smooth and subsample a matrix while preserving its original scale.

    Zero padding is intentionally avoided: depth maps use zero for invalid
    pixels, and treating those zeros as measurements creates dark borders and
    false peaks around holes.  Callers that need a validity mask should use
    :func:`_downsample_depth` so both arrays use the same weighted kernel.
    """
    matrix = np.asarray(matrix)
    kernel_size = int(kernel_size)
    if matrix.ndim != 2:
        raise ValueError("matrix must be a two-dimensional array")
    kernel = gaussian_kernel(kernel_size)
    weights = convolve(np.ones(matrix.shape, dtype=np.float64), kernel, mode="nearest")
    smoothed = convolve(matrix.astype(np.float64, copy=False), kernel, mode="nearest")
    smoothed = np.divide(smoothed, weights, out=np.zeros_like(smoothed), where=weights > 0)
    return smoothed[::kernel_size, ::kernel_size]


def _downsample_depth(depth, valid_mask, kernel_size, median_size):
    """Smooth measured values without filling holes or lowering their edges."""
    depth = np.asarray(depth, dtype=np.float64)
    valid_mask = np.asarray(valid_mask, dtype=bool)
    if depth.ndim != 2 or valid_mask.shape != depth.shape:
        raise ValueError("depth and valid_mask must be two-dimensional arrays of equal shape")
    finite_mask = valid_mask & np.isfinite(depth) & (depth > 0)
    values = np.where(finite_mask, depth, 0.0)
    median_size = int(median_size)
    kernel_size = int(kernel_size)
    if median_size < 1 or kernel_size < 1:
        raise ValueError("median size and downsample size must be positive")
    if median_size > 1:
        # A zero-filled median would depress the ring boundary. Keep measured
        # values there; filter only neighborhoods consisting entirely of data.
        complete = minimum_filter(finite_mask, size=median_size, mode="nearest")
        filtered = median_filter(values, size=median_size, mode="nearest")
        values[complete] = filtered[complete]
        del complete, filtered
    kernel = gaussian_kernel(kernel_size)
    coverage = convolve(finite_mask.astype(np.float64), kernel, mode="nearest")
    weighted_depth = convolve(values, kernel, mode="nearest")
    smoothed = np.divide(weighted_depth, coverage, out=np.zeros_like(weighted_depth), where=coverage > 1e-12)
    # Never manufacture a point where the actual sampled sensor pixel is void.
    return smoothed[::kernel_size, ::kernel_size], finite_mask[::kernel_size, ::kernel_size].copy()


def _sampled_cell_mask(valid_mask, step):
    """Disallow faces crossing any unsampled invalid pixel between vertices."""
    valid_mask = np.asarray(valid_mask, dtype=bool)
    rows = np.arange(0, valid_mask.shape[0], step)
    cols = np.arange(0, valid_mask.shape[1], step)
    # Integral image evaluates all source rectangles in O(pixel_count) time.
    invalid = np.pad((~valid_mask).astype(np.uint32), ((1, 0), (1, 0)))
    np.cumsum(invalid, axis=0, dtype=np.uint32, out=invalid)
    np.cumsum(invalid, axis=1, dtype=np.uint32, out=invalid)
    top, bottom = rows[:-1, None], rows[1:, None] + 1
    left, right = cols[None, :-1], cols[None, 1:] + 1
    counts = invalid[bottom, right] - invalid[top, right] - invalid[bottom, left] + invalid[top, left]
    return counts == 0


def filter_outliers(matrix, threshold=2):
    """过滤偏离平均值过大的数据。"""
    mean = np.mean(matrix)
    std_dev = np.std(matrix)
    return np.where(np.abs(matrix - mean) < threshold * std_dev, matrix, mean)


def apply_jet_colormap(z_coords, minV=None, maxV=None):
    """将 z 坐标应用 jet 颜色映射（使用 OpenCV LUT）。"""
    if minV is None:
        minV = np.min(z_coords)
    if maxV is None:
        maxV = np.max(z_coords)
    if minV > maxV:
        minV, maxV = maxV, minV
    norm = Normalize(vmin=minV, vmax=maxV, clip=True)
    cmap = colormaps.get_cmap('jet')
    return cmap(norm(z_coords))


def _as_finite_point_cloud(point_cloud, *, minimum_points=3):
    points = np.asarray(point_cloud, dtype=np.float64)
    if points.ndim != 2 or points.shape[1] != 3:
        raise ValueError("point_cloud must have shape (N, 3)")
    finite = np.isfinite(points).all(axis=1)
    points = points[finite]
    if points.shape[0] < minimum_points:
        raise ValueError(f"at least {minimum_points} finite points are required")
    return points


def generate_mesh_from_point_cloud_pcl(point_cloud):
    """
    使用 PCL 从点云生成三角网格。

    point_cloud: (N, 3) numpy 数组
        输入的点云数据，每个点包含 x, y, z 坐标。

    返回:
        mesh: open3d.geometry.TriangleMesh
            生成的三角网格。
    """
    import trimesh

    points = _as_finite_point_cloud(point_cloud)
    # Duplicate XY samples make Qhull fail even when their Z values differ.
    # Keep the first sample so every generated face refers to a stable vertex.
    _, unique_indices = np.unique(points[:, :2], axis=0, return_index=True)
    points = points[np.sort(unique_indices)]
    if points.shape[0] < 3:
        raise ValueError("at least three unique XY points are required")
    try:
        delaunay = Delaunay(points[:, :2])
    except QhullError as exc:
        raise ValueError("point cloud XY coordinates are degenerate") from exc
    triangles = delaunay.simplices

    mesh = trimesh.Trimesh(vertices=points, faces=triangles, process=False)
    return mesh


def generate_mesh_from_point_cloud_optimized(point_cloud, voxel_size=0.05, poisson_depth=9):
    """
    从点云生成三角网格（经过体素化优化）。

    point_cloud: (N, 3) numpy 数组
        输入的点云数据，每个点包含 x, y, z 坐标。

    voxel_size: float
        体素大小，用于下采样点云。

    返回:
        mesh: open3d.geometry.TriangleMesh
            生成的三角网格。
    """
    points = _as_finite_point_cloud(point_cloud)
    try:
        voxel_size = float(voxel_size)
        poisson_depth = int(poisson_depth)
    except (TypeError, ValueError) as exc:
        raise ValueError("voxel_size and poisson_depth must be numeric") from exc
    if not np.isfinite(voxel_size) or voxel_size <= 0:
        raise ValueError("voxel_size must be a positive finite number")
    if not 2 <= poisson_depth <= 12:
        raise ValueError("poisson_depth must be between 2 and 12")

    # 将点云转化为 Open3D 点云对象
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(points)

    # 进行体素化下采样
    pcd_downsampled = pcd.voxel_down_sample(voxel_size)

    if len(pcd_downsampled.points) < 3:
        raise ValueError("voxel downsampling left fewer than three points")

    # 计算点云法线.  The radius scales with the input resolution; a fixed
    # 0.1 radius made normal estimation fail for millimetre-scale scans.
    radius = max(voxel_size * 2.5, np.finfo(float).eps)
    pcd_downsampled.estimate_normals(
        search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=radius, max_nn=30))

    # 使用 Poisson 重建生成网格
    mesh, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(
        pcd_downsampled, depth=poisson_depth)

    # 计算法线（如果需要）
    mesh.compute_vertex_normals()

    if len(mesh.triangles) == 0:
        raise ValueError("Poisson reconstruction returned no triangles")
    return mesh


def generate_mesh_from_grid(x_coords, y_coords, z_coords, valid_mask, max_cell_z_span=300,
                            cell_valid_mask=None):
    """Build local surface triangles without spanning holes or depth jumps."""
    coordinates = [np.asarray(values, dtype=np.float64) for values in (x_coords, y_coords, z_coords)]
    valid_mask = np.asarray(valid_mask, dtype=bool).copy()
    shape = coordinates[0].shape
    if len(shape) != 2 or any(values.shape != shape for values in coordinates) or valid_mask.shape != shape:
        raise ValueError("coordinate arrays and valid_mask must have equal 2D shapes")
    max_cell_z_span = float(max_cell_z_span)
    if not np.isfinite(max_cell_z_span) or max_cell_z_span < 0:
        raise ValueError("max_cell_z_span must be a non-negative finite number")
    grid = np.stack(coordinates, axis=-1)
    valid_mask &= np.isfinite(grid).all(axis=-1)
    if np.count_nonzero(valid_mask) < 3:
        raise ValueError("empty point cloud, cannot build mesh")
    indexes = np.full(shape, -1, dtype=np.int32)
    indexes[valid_mask] = np.arange(np.count_nonzero(valid_mask), dtype=np.int32)
    vertices = grid[valid_mask]
    # +Z winding for x=column and y=row. Only immediate grid neighbors connect.
    triangles = np.stack((
        np.stack((indexes[:-1, :-1], indexes[:-1, 1:], indexes[1:, :-1]), axis=-1),
        np.stack((indexes[1:, :-1], indexes[:-1, 1:], indexes[1:, 1:]), axis=-1),
    ), axis=-2)
    usable = (triangles >= 0).all(axis=-1)
    if cell_valid_mask is not None:
        cells = np.asarray(cell_valid_mask, dtype=bool)
        if cells.shape != (max(shape[0] - 1, 0), max(shape[1] - 1, 0)):
            raise ValueError("cell_valid_mask must describe every grid cell")
        usable &= cells[..., None]
    triangles = triangles[usable]
    if triangles.size:
        points = vertices[triangles]
        areas = np.linalg.norm(np.cross(points[:, 1] - points[:, 0], points[:, 2] - points[:, 0]), axis=1)
        triangles = triangles[(areas > np.finfo(float).eps) & (np.ptp(points[:, :, 2], axis=1) <= max_cell_z_span)]
    if not triangles.size:
        raise ValueError("no valid surface triangles, cannot build mesh")
    used, inverse = np.unique(triangles, return_inverse=True)
    vertices = vertices[used]
    triangles = inverse.reshape(-1, 3).astype(np.int32)
    mesh = o3d.geometry.TriangleMesh()
    mesh.vertices = o3d.utility.Vector3dVector(vertices)
    mesh.triangles = o3d.utility.Vector3iVector(triangles)
    mesh.compute_vertex_normals()
    return mesh, vertices


def save_colored_obj(mesh, colors, filename):
    """Write an Open3D mesh as OBJ, optionally attaching per-vertex colors.

    Open3D silently drops malformed color arrays, so validate and normalize
    them here.  The return value follows ``write_triangle_mesh`` and is False
    when the writer rejects the mesh.
    """
    if not isinstance(mesh, o3d.geometry.TriangleMesh):
        raise TypeError("mesh must be an open3d TriangleMesh")
    output = Path(filename)
    output.parent.mkdir(parents=True, exist_ok=True)
    if len(mesh.vertices) == 0 or len(mesh.triangles) == 0:
        raise ValueError("cannot write an empty triangle mesh")

    has_colors = colors is not None
    if has_colors:
        color_array = np.array(colors, dtype=np.float64, copy=True)
        if color_array.ndim != 2 or color_array.shape[0] != len(mesh.vertices) or color_array.shape[1] not in (3, 4):
            raise ValueError("colors must have shape (vertex_count, 3) or (vertex_count, 4)")
        if not np.isfinite(color_array).all():
            raise ValueError("colors must contain only finite values")
        if color_array.shape[1] == 4:
            color_array = color_array[:, :3]
        if color_array.max(initial=0) > 1.0:
            color_array /= 255.0
        if color_array.min(initial=0) < 0 or color_array.max(initial=0) > 1:
            raise ValueError("colors must be in [0, 1] or [0, 255]")
        mesh.vertex_colors = o3d.utility.Vector3dVector(color_array)

    # Keep the last valid OBJ visible until a complete replacement is ready.
    with NamedTemporaryFile(dir=output.parent, prefix=f".{output.stem}-", suffix=".obj", delete=False) as temporary:
        temporary_path = Path(temporary.name)
    try:
        if not o3d.io.write_triangle_mesh(str(temporary_path), mesh, write_triangle_uvs=False):
            return False
        if temporary_path.stat().st_size == 0:
            return False
        os.replace(temporary_path, output)
        return True
    finally:
        temporary_path.unlink(missing_ok=True)


def toMesh(obj, managerQueue=None):
    """Run Qt's Balsam optimizer when available.

    Mesh generation remains useful without Balsam (for example on a test or
    development host), so a missing executable is reported as a false result
    rather than raising from the worker thread.  ``managerQueue`` is retained
    for API compatibility with the original saver.
    """
    obj_path = Path(obj).resolve()
    if not obj_path.is_file():
        logger.error("optimize mesh input does not exist: %s", obj_path)
        return False
    configured = getattr(serverConfigProperty, "balsam_exe", None)
    executable = str(configured or "").strip()
    if not executable:
        logger.warning("balsam executable is not configured; keep unoptimized OBJ: %s", obj_path)
        return False
    resolved = str(Path(executable).resolve()) if Path(executable).is_file() else shutil.which(executable)
    if not resolved:
        logger.warning("balsam executable is unavailable; keep unoptimized OBJ: %s", executable)
        return False

    cmd = [str(resolved), "--optimizeMeshes", str(obj_path)]
    logger.debug("optimize mesh command: %s", cmd)
    try:
        result = subprocess.run(
            cmd,
            cwd=str(obj_path.parent),
            env=os.environ.copy(),
            timeout=_get_balsam_timeout(),
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            errors="replace",
        )
        if result.returncode != 0:
            logger.error("optimize mesh failed with exit code %s: obj=%s stderr=%s", result.returncode, obj_path,
                         (result.stderr or "").strip()[-500:])
            return False
    except subprocess.TimeoutExpired:
        logger.error("optimize mesh timed out after %ss: obj=%s", _get_balsam_timeout(), obj_path)
        return False
    except OSError as exc:
        logger.error("optimize mesh could not start: obj=%s error=%s", obj_path, exc)
        return False
    logger.debug("optimize mesh finished: %s", obj_path)
    return True


def _get_point_cloud_(data, managerQueue):
    """Convert the eight-field legacy or nine-field calibrated job to mm."""
    if not isinstance(data, (tuple, list)) or len(data) not in (8, 9):
        raise ValueError("3D save data must contain eight or nine fields")
    coil_id, depth, mask, config_data, circle_config, save_file, baseline_mm, precision = data[:8]
    depth = np.asarray(depth, dtype=np.float64)
    mask = np.asarray(mask)
    if depth.ndim != 2 or mask.shape != depth.shape:
        raise ValueError("depth data and mask must be equal 2D arrays")
    try:
        scale_x, scale_y, scale_z = (float(value) for value in precision)
        offset_z = float(data[8]) if len(data) == 9 else 0.0
        baseline_mm = float(baseline_mm)
        step = int(Globs.control.downsampleSize)
        median_size = int(Globs.control.median_filter_size)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("invalid 3D calibration or filter configuration") from exc
    if not all(np.isfinite(value) and value > 0 for value in (scale_x, scale_y, scale_z)):
        raise ValueError("3D pixel precision must be positive and finite")
    if not np.isfinite(offset_z) or not np.isfinite(baseline_mm):
        raise ValueError("3D offset and baseline must be finite")
    if step < 1 or median_size < 1:
        raise ValueError("3D filter sizes must be positive")
    valid = (mask > 0) & np.isfinite(depth) & (depth > 0)
    sampled, sampled_valid = _downsample_depth(depth, valid, step, median_size)
    try:
        cx, cy = (float(value) for value in circle_config["inner_circle"]["ellipse"][0])
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise ValueError("circleConfig does not contain inner_circle ellipse center") from exc
    if not np.isfinite(cx) or not np.isfinite(cy):
        raise ValueError("circle center must be finite")
    rows, cols = sampled.shape
    x_coords, y_coords = np.meshgrid(
        (np.arange(cols, dtype=np.float64) * step - cx) * scale_x,
        (np.arange(rows, dtype=np.float64) * step - cy) * scale_y,
    )
    z_coords = sampled * scale_z + offset_z - baseline_mm
    # Preserve the existing relative height limits without reinstating rejected
    # outliers when fewer than 1000 points remain.
    sampled_valid &= np.isfinite(z_coords) & (z_coords >= -500) & (z_coords <= 1000)
    grid = np.stack((x_coords, y_coords, z_coords), axis=-1)
    return {
        "point_cloud": grid[sampled_valid],
        "x_coords": x_coords,
        "y_coords": y_coords,
        "z_coords": z_coords,
        "valid_mask": sampled_valid,
        "cell_valid_mask": _sampled_cell_mask(valid, step),
    }, save_file


def _write_mesh_status(save_file, coil_id, state, *, optimizer_success=None, error=None):
    """Publish the asynchronous mesh result without exposing the depth payload."""
    output = Path(save_file)
    status = {
        "schema_version": 1,
        "coil_id": str(coil_id),
        "state": state,
        "obj_file": output.name,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "optimizer_success": optimizer_success,
    }
    if error is not None:
        status["error"] = str(error)
    temporary_path = None
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(mode="w", dir=output.parent, prefix=".mesh_status-", suffix=".json",
                                encoding="utf-8", delete=False) as temporary:
            temporary_path = Path(temporary.name)
            json.dump(status, temporary, ensure_ascii=False, allow_nan=False)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_path, output.with_name("mesh_status.json"))
        return True
    except OSError as exc:
        logger.error("failed to publish mesh status for %s: %s", output, exc)
        return False
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def _record_rejected_mesh_task(task, reason):
    """Do not leave an old successful status behind for a rejected rebuild."""
    if not isinstance(task, (tuple, list)) or len(task) not in (8, 9):
        return
    if not isinstance(task[5], (str, os.PathLike)):
        return
    _write_mesh_status(task[5], task[0], "error", error=reason)


def _save_3d(data, managerQueue):
    save_file = data[5]
    coil_id = data[0]
    _write_mesh_status(save_file, coil_id, "processing")
    started = time.monotonic()
    try:
        result, save_file = _get_point_cloud_(data, managerQueue)
        if result["point_cloud"].shape[0] < 3:
            raise ValueError("not enough valid depth points to build a mesh")
        mesh, _ = generate_mesh_from_grid(
            result["x_coords"], result["y_coords"], result["z_coords"], result["valid_mask"],
            cell_valid_mask=result.get("cell_valid_mask"),
        )
        if not save_colored_obj(mesh, None, str(save_file)):
            raise OSError("Open3D failed to write the OBJ mesh")
        # OBJ consumers can display this complete model while Qt conversion
        # runs. Conversion failure does not invalidate a usable OBJ.
        _write_mesh_status(save_file, coil_id, "ready")
        optimized = toMesh(str(save_file), managerQueue)
        _write_mesh_status(save_file, coil_id, "ready", optimizer_success=optimized)
        logger.debug("3D mesh ready: coil=%s output=%s elapsed=%.3fs", coil_id, save_file,
                     time.monotonic() - started)
        return True
    except Exception as exc:
        _write_mesh_status(save_file, coil_id, "error", error=exc)
        logger.exception("3D mesh generation failed: coil=%s output=%s", coil_id, save_file)
        return False


class D3Saver:
    """
    使用多进程执行
    """

    def __init__(self, managerQueue, loggerProcess):
        self.managerQueue = managerQueue
        try:
            self.num_processes = max(int(Globs.control.D3SaverWorkNum), 1)
            queue_size = max(int(Globs.control.D3SaverThreadMaxsize), 1)
        except (AttributeError, TypeError, ValueError) as exc:
            raise ValueError("invalid D3 saver worker or queue configuration") from exc
        self.type_ = Globs.control.D3SaverThreadType
        self.queue_put_timeout = _get_d3_queue_put_timeout()
        self.join_timeout = _get_d3_join_timeout()
        self._state_lock = threading.Lock()
        self._joined = False
        if self.type_ == "multiprocessing":
            self.queue = MulQueue(maxsize=queue_size)
            self._stop_event = multiprocessing.Event()
        else:
            self.queue = ThreadQueue(maxsize=queue_size)
            self._stop_event = threading.Event()
        self.processes = []
        self._initialize_processes()

    def _initialize_processes(self):
        for _ in range(self.num_processes):
            if self.type_ == "multiprocessing":
                process = multiprocessing.Process(target=self._save_3d,
                                                  args=(self.queue, self.managerQueue, self._stop_event))
            else:
                process = threading.Thread(target=self._save_3d,
                                           args=(self.queue, self.managerQueue, self._stop_event))
            process.daemon = True
            self.processes.append(process)
            process.start()

    def add_(self, *args) -> bool:
        task = args[0] if len(args) == 1 else args
        try:
            # Serialize acceptance with the insertion of shutdown sentinels.
            with self._state_lock:
                if self._joined:
                    logger.warning("3DSaver rejected task after shutdown")
                    _record_rejected_mesh_task(task, "3D mesh rebuild rejected: saver is shut down")
                    return False
                self.queue.put(task, timeout=self.queue_put_timeout)
            try:
                queue_size = self.queue.qsize()
            except (AttributeError, NotImplementedError):
                queue_size = "unknown"
            logger.debug("3DSaver queue size=%s", queue_size)
            return True
        except Full:
            logger.error("3DSaver queue full, drop 3D mesh save task")
            _record_rejected_mesh_task(task, "3D mesh rebuild rejected: save queue is full")
        except Exception as e:
            logger.exception("3DSaver queue put failed: %s", e)
            _record_rejected_mesh_task(task, f"3D mesh rebuild could not be queued: {e}")
        return False

    @staticmethod
    def _save_3d(queue, managerQueue, stop_event=None):
        while True:
            try:
                data = queue.get(timeout=0.2)
            except Empty:
                if stop_event is not None and stop_event.is_set():
                    break
                continue
            except (EOFError, OSError) as exc:
                logger.error("3DSaver worker queue closed: %s", exc)
                break
            if data is None:
                queue.task_done()
                break
            try:
                if not Globs.control.save_3d_obj:
                    logger.debug("skip 3D mesh save because save_3d_obj is disabled")
                    continue
                _save_3d(data, managerQueue)
            except Exception:
                logger.exception("Failed to save 3D mesh")
            finally:
                queue.task_done()
                # Mesh jobs contain the full depth and mask arrays. Do not
                # retain the previous job while waiting on an empty queue.
                data = None

    def join(self):
        """Drain queued jobs and stop workers within the configured deadline."""
        with self._state_lock:
            if self._joined:
                return
            self._joined = True
        deadline = time.monotonic() + self.join_timeout
        sent_stop_count = 0
        while sent_stop_count < self.num_processes:
            timeout = max(min(self.queue_put_timeout, deadline - time.monotonic()), 0.1)
            try:
                self.queue.put(None, timeout=timeout)
                sent_stop_count += 1
            except Full:
                if time.monotonic() >= deadline:
                    logger.error(
                        "3DSaver shutdown timed out while sending stop signals: sent=%s/%s",
                        sent_stop_count,
                        self.num_processes,
                    )
                    self._stop_event.set()
                    break
            except Exception as e:
                logger.exception("3DSaver shutdown failed while sending stop signal: %s", e)
                self._stop_event.set()
                break
        # 停止所有进程
        for process in self.processes:
            # Share one shutdown deadline across the worker pool.
            remaining = max(deadline - time.monotonic(), 0.1)
            original_timeout = self.join_timeout
            self.join_timeout = min(original_timeout, remaining)
            try:
                process.join(timeout=self.join_timeout)
            finally:
                self.join_timeout = original_timeout
            if process.is_alive():
                self._stop_event.set()
                logger.warning("3DSaver worker did not exit within %ss: %s", self.join_timeout, process)
                terminate = getattr(process, "terminate", None)
                if callable(terminate):
                    terminate()
                    process.join(timeout=2)
