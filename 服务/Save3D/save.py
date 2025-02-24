import os
import subprocess
import time
import traceback

from matplotlib.colors import Normalize
from matplotlib.pyplot import get_cmap

from CONFIG import serverConfigProperty
from threading import Thread
import threading
import multiprocessing
from multiprocessing import JoinableQueue as MulQueue
from queue import Queue as ThreadQueue
from utils.Log import logger
import Globs


def gaussian_kernel(size, sigma=1):
    """生成高斯卷积核。"""
    kernel_1D = np.linspace(-(size // 2), size // 2, size)
    for i in range(size):
        kernel_1D[i] = np.exp(-0.5 * (kernel_1D[i] / sigma) ** 2)
    kernel_1D /= kernel_1D.sum()
    kernel_2D = np.outer(kernel_1D, kernel_1D)
    kernel_2D /= kernel_2D.sum()
    return kernel_2D


def downsample_data_with_convolution(matrix, kernel_size):
    """通过卷积对矩阵进行下采样。"""
    kernel = gaussian_kernel(kernel_size)
    from scipy.ndimage import convolve
    downsampled_matrix = convolve(matrix, kernel, mode='constant', cval=0.0)
    return downsampled_matrix[::kernel_size, ::kernel_size]


def filter_outliers(matrix, threshold=2):
    """过滤偏离平均值过大的数据。"""
    mean = np.mean(matrix)
    std_dev = np.std(matrix)
    return np.where(np.abs(matrix - mean) < threshold * std_dev, matrix, mean)


def apply_jet_colormap(z_coords, minV=None, maxV=None):
    """将 z 坐标应用 jet 颜色映射。"""
    # 如果 minV 或 maxV 没有提供，则使用 z_coords 的最小值和最大值
    if minV is None:
        minV = np.min(z_coords)
    print(f"minV: {minV}  {np.min(z_coords)}")
    print(f"maxV: {maxV}  {np.max(z_coords)}")
    if maxV is None:
        maxV = np.max(z_coords)
    # 确保 minV <= maxV
    if minV > maxV:
        minV, maxV = maxV, minV
    norm = Normalize(vmin=minV, vmax=maxV, clip=True)
    cmap = get_cmap('jet')
    return cmap(norm(z_coords))


import numpy as np


def generate_mesh_from_point_cloud_pcl(point_cloud):
    """
    使用 PCL 从点云生成三角网格。

    point_cloud: (N, 3) numpy 数组
        输入的点云数据，每个点包含 x, y, z 坐标。

    返回:
        mesh: open3d.geometry.TriangleMesh
            生成的三角网格。
    """
    from scipy.spatial import Delaunay
    import trimesh

    # 使用 Delaunay 三角剖分
    delaunay = Delaunay(point_cloud[:, :2])  # 只使用 x, y 坐标进行三角剖分
    triangles = delaunay.simplices

    # 创建 Trimesh 网格
    mesh = trimesh.Trimesh(vertices=point_cloud, faces=triangles)

    # 可视化网格
    mesh.show()


import open3d as o3d


# from scipy.spatial import Delaunay


def generate_mesh_from_point_cloud_optimized(point_cloud, voxel_size=0.05):
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
    # 将点云转化为 Open3D 点云对象
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(point_cloud)

    # 进行体素化下采样
    pcd_downsampled = pcd.voxel_down_sample(voxel_size)

    # 计算点云法线
    pcd_downsampled.estimate_normals(search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=0.1, max_nn=30))

    # 使用 Poisson 重建生成网格
    mesh, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(pcd_downsampled, depth=9)

    # 计算法线（如果需要）
    mesh.compute_vertex_normals()

    return mesh


# def generate_mesh_from_point_cloud(point_cloud):
#     """
#     从点云生成三角网格。
#
#     point_cloud: (N, 3) numpy 数组
#         输入的点云数据，每个点包含 x, y, z 坐标。
#
#     返回:
#         mesh: open3d.geometry.TriangleMesh
#             生成的三角网格。
#     """
#     points = point_cloud[:, :2]  # 只使用 x 和 y 坐标进行 Delaunay 三角剖分
#     tri = Delaunay(points)  # 使用 Delaunay 进行二维三角剖分
#     triangles = tri.simplices  # 获取三角形的索引
#
#     # 创建 Open3D 的 TriangleMesh 对象
#     mesh = o3d.geometry.TriangleMesh()
#     mesh.vertices = o3d.utility.Vector3dVector(point_cloud)  # 使用完整的 x, y, z 坐标作为顶点
#     mesh.triangles = o3d.utility.Vector3iVector(triangles)  # 设置三角形面
#     mesh.compute_vertex_normals()  # 计算每个顶点的法线
#
#     return mesh

def generate_mesh_from_point_cloud(point_cloud):
    import open3d as o3d
    from scipy.spatial import Delaunay
    """从点云生成三角网格。"""
    points = point_cloud[:, :2]  # 只使用x和y坐标进行Delaunay三角剖分
    print(f"point_cloud points shape: {points.shape}")
    tri = Delaunay(points, incremental=True)
    triangles = tri.simplices
    mesh = o3d.geometry.TriangleMesh()
    mesh.vertices = o3d.utility.Vector3dVector(point_cloud)
    mesh.triangles = o3d.utility.Vector3iVector(triangles)
    mesh.compute_vertex_normals()

    return mesh


def save_colored_obj(mesh, colors, filename):
    """将彩色网格保存为 .obj 文件。"""
    return o3d.io.write_triangle_mesh(filename, mesh)
    with open(filename, 'w') as f:
        for vertex, color in zip(np.asarray(mesh.vertices), colors):
            colorStr = f"{color[0]} {color[1]} {color[2]}"
            f.write(f"v {vertex[0]} {vertex[1]} {colorStr} {color[2]}\n")
        for triangle in np.asarray(mesh.triangles):
            f.write(f"f {triangle[0] + 1} {triangle[1] + 1} {triangle[2] + 1}\n")
        # for triangle in np.asarray(mesh.triangles) + 1:
        #     f.write(f"f {triangle[0]} {triangle[1]} {triangle[2]}\n")


def toMesh(obj, managerQueue):
    cmdBalsam = serverConfigProperty.balsam_exe
    cmd = f"{cmdBalsam} --optimizeMeshes {obj}"
    print(cmd)
    try:
        workPath = os.path.dirname(obj)
        env = os.environ.copy()
        subprocess.check_call(cmd, shell=True, cwd=workPath,env=env)
    except BaseException as e:
        print(e)
    print(cmd + "end")
    # os.system(cmd)
    # managerQueue.put(["cmd",cmd,workPath])


def _get_point_cloud_(data, managerQueue):
    from scipy.ndimage import median_filter
    coilId, npyData, mask, configDatas, circleConfig, saveFile, median_non_mm, [pixel_x_precision, pixel_y_precision,
                                                                                pixel_z_precision] = data
    npyData[mask == 0] = 0
    matrix = median_filter(npyData, size=Globs.control.median_filter_size)
    # 对数据进行下采样
    matrix = downsample_data_with_convolution(matrix, Globs.control.downsampleSize)
    rows, cols = matrix.shape
    cx, cy = circleConfig["inner_circle"]['ellipse'][0]  # 中心点x坐标
    # 生成x和y坐标的网格
    x_indices = np.arange(rows) - cx
    y_indices = np.arange(cols) - cy
    x_coords, y_coords = np.meshgrid(x_indices, y_indices, indexing='ij')
    # 计算x, y, z坐标
    x_coords = x_coords * pixel_x_precision
    y_coords = y_coords * pixel_y_precision
    z_coords = matrix * pixel_z_precision
    # 合并x, y, z坐标
    point_cloud = np.stack((x_coords, y_coords, z_coords), axis=-1).reshape(-1, 3)
    mean_values2 = point_cloud.mean(axis=0)

    # 删除z < 0 的点
    # point_cloud = point_cloud[point_cloud[:, 2] >= 10]

    mean_values2[2] = median_non_mm
    point_cloud[:, :] -= mean_values2
    # print("point_cloud.mean")
    # print(point_cloud.mean(axis=0))

    point_cloud = point_cloud[point_cloud[:, 2] >= - 150]
    point_cloud = point_cloud[point_cloud[:, 2] <= 500]
    return point_cloud, saveFile


def _save_3d(data, managerQueue):
    t0 = time.time()
    point_cloud, saveFile = _get_point_cloud_(data, managerQueue)
    t1 = time.time()
    logger.debug(f"_get_point_cloud_  {t1 - t0}")
    colors = apply_jet_colormap(point_cloud[:, 2], minV=-200, maxV=200)
    t2 = time.time()
    logger.debug(f"apply_jet_colormap {t2 - t1}")
    colors = colors[:, :3]  # 只保留 RGB 通道
    # 使用Delaunay三角剖分生成三角网格
    # mesh=generate_mesh_from_point_cloud_pcl(point_cloud)
    mesh = generate_mesh_from_point_cloud(point_cloud)

    t3 = time.time()
    logger.debug(f"generate_mesh_from_point_cloud {t3 - t2}")
    # o3d.visualization.draw_geometries([mesh])
    # 保存彩色的.obj文件
    save_colored_obj(mesh, colors, str(saveFile))
    t4 = time.time()
    logger.debug(f"save_colored_obj {t4 - t3}")
    Thread(target=toMesh,args=(str(saveFile), managerQueue)).start()
    # toMesh(str(saveFile), managerQueue)
    logger.debug("toMesh end")


class D3Saver:
    """
    使用多进程执行
    """

    def __init__(self, managerQueue, loggerProcess):
        self.managerQueue = managerQueue
        self.num_processes = Globs.control.D3SaverWorkNum
        self.type_ = Globs.control.D3SaverThreadType
        if self.type_ == "multiprocessing":
            self.queue = MulQueue(maxsize=Globs.control.D3SaverThreadMaxsize)
        else:
            self.queue = ThreadQueue(maxsize=Globs.control.D3SaverThreadMaxsize)
        self.processes = []
        self._initialize_processes()

    def _initialize_processes(self):
        for _ in range(self.num_processes):
            if self.type_ == "multiprocessing":
                process = multiprocessing.Process(target=self._save_3d, args=(self.queue, self.managerQueue))
            else:
                process = threading.Thread(target=self._save_3d, args=(self.queue, self.managerQueue))
            process.daemon = True
            self.processes.append(process)
            process.start()

    def add_(self, *args):
        self.queue.put(*args)
        print(f"3DSaver add_   队列 size {self.queue.qsize()}")

    @staticmethod
    def _save_3d(queue, managerQueue):
        while True:
            data = queue.get()
            if data is None:
                break
            try:
                if not Globs.control.save_3d_obj:
                    return
                _save_3d(data, managerQueue)
            except Exception as e:
                error_message = traceback.format_exc()
                print(f"Failed to save  {error_message}")
            finally:
                queue.task_done()

    def join(self):
        # 阻塞直到所有任务完成
        self.queue.join()
        # 停止所有进程
        for _ in range(self.num_processes):
            self.queue.put((None, None, None))
        for process in self.processes:
            process.join()
