import numpy as np
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
from scipy.spatial.transform import Rotation as R
from scipy.stats import norm


def fit_plane(x_, y_, z):
    """
    使用线性回归拟合一个平面，返回平面方程的系数（a, b, c），
    以及平面法向量
    """
    X = np.vstack((x_, y_)).T
    model = LinearRegression()
    model.fit(X, z)
    a_, b_ = model.coef_
    c_ = model.intercept_
    # 返回平面方程的系数
    return a_, b_, c_


def rotate_data(data, normal_vector):
    """
    使用旋转矩阵旋转数据，将法向量旋转到 Z 轴
    """
    # 目标是将法向量 normal_vector 旋转到 Z 轴
    target_normal = np.array([0, 0, 1])  # Z轴方向
    axis_of_rotation = np.cross(normal_vector, target_normal)  # 计算旋转轴
    angle_of_rotation = np.arccos(np.dot(normal_vector, target_normal) / (
            np.linalg.norm(normal_vector) * np.linalg.norm(target_normal)))  # 计算旋转角度
    if np.linalg.norm(axis_of_rotation) == 0:
        return data  # 如果已经平行于Z轴，返回原数据

    # 归一化旋转轴
    axis_of_rotation = axis_of_rotation / np.linalg.norm(axis_of_rotation)

    # 创建旋转矩阵
    rotation = R.from_rotvec(axis_of_rotation * angle_of_rotation)
    rotation_matrix = rotation.as_matrix()

    # 对数据应用旋转矩阵
    shape = data.shape
    x, y = np.meshgrid(np.arange(shape[1]), np.arange(shape[0]))
    coords = np.vstack([x.flatten(), y.flatten(), data.flatten()])

    rotated_coords = np.dot(rotation_matrix, coords)  # 旋转后的坐标
    rotated_data = rotated_coords[2, :].reshape(shape)

    return rotated_data


def plot_surface(data, title="Surface"):
    """
    可视化表面
    """
    x = np.arange(0, data.shape[1])
    y = np.arange(0, data.shape[0])
    X, Y = np.meshgrid(x, y)
    Z = data

    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    ax.plot_surface(X, Y, Z, cmap='viridis')
    ax.set_title(title)
    plt.show()


def flatten_surface_by_rotation(data):
    """
    通过旋转数据使其接近平行的平面
    """
    rows, cols = data.shape
    x, y = np.meshgrid(np.arange(cols), np.arange(rows))  # 获取X和Y的下标
    x = x.flatten()
    y = y.flatten()
    z = data.flatten()

    # 过滤掉为0的数据
    non_zero_indices = z > 10
    x = x[non_zero_indices]
    y = y[non_zero_indices]
    z = z[non_zero_indices]
    print(np.mean(z))

    # 拟合平面并计算平面方程的系数
    a, b, c = fit_plane(x, y, z)
    print(f"拟合平面方程: z = {a}*x + {b}*y + {c}")

    # 旋转数据使其法向量对齐到Z轴
    rotated_data = rotate_data(data, np.array([a, b, 1]))

    return a, b, c, rotated_data


def get_reference_z_values(x, y, a, b, c):
    """
    根据平面方程计算参考平面上每个 (x, y) 的 Z 值
    """
    return a * x + b * y + c


def extract_normal_distribution_z_values(data):
    """
    提取旋转后的平面中心部分的 Z 值，并检查其是否遵循正态分布
    """
    # 获取中心区域
    center_region = data[data.shape[0] // 4:data.shape[0] // 2 + data.shape[0] // 4,
                    data.shape[1] // 4:data.shape[1] // 2 + data.shape[1] // 4]

    # 提取该区域的所有 Z 值（去除为0的数据）
    z_values = center_region[center_region != 0]

    # 可视化该区域的 Z 值的直方图
    plt.hist(z_values, bins=50, density=True, alpha=0.6, color='g')

    # 拟合正态分布
    mu, std = norm.fit(z_values)
    xmin, xmax = plt.xlim()
    x = np.linspace(xmin, xmax, 100)
    p = norm.pdf(x, mu, std)
    plt.plot(x, p, 'k', linewidth=2)
    title = "Fit results: mu = %.2f,  std = %.2f" % (mu, std)
    plt.title(title)
    plt.show()

    return mu, std


if __name__ == "__main__":
    # 加载 npz 数据
    Z_noisy = np.load("2.npz")['array']
    print("原始数据形状:", Z_noisy.shape)

    # 可视化原始数据
    plot_surface(Z_noisy, title="Noisy Surface")

    # 旋转数据使其平行
    a, b, c, rotated_data = flatten_surface_by_rotation(Z_noisy)
    print("旋转后的数据形状:", rotated_data.shape)

    # 可视化旋转后的数据
    plot_surface(rotated_data, title="Rotated Surface")

    # 获取参考平面上每个 (x, y) 的 Z 值
    rows, cols = Z_noisy.shape
    x, y = np.meshgrid(np.arange(cols), np.arange(rows))
    reference_z_values = get_reference_z_values(x, y, a, b, c)

    # 获取旋转后平面中心区域的 Z 值并进行正态分布拟合
    mu, std = extract_normal_distribution_z_values(rotated_data)
    print(f"正态分布的均值: {mu}, 标准差: {std}")
