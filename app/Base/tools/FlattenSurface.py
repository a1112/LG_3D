import numpy as np
from scipy.stats import norm
from scipy.spatial.transform import Rotation as R


def fit_plane(x_, y_, z):
    """
    使用线性回归拟合一个平面，返回平面方程的系数 (a, b, c) 和法向量。
    """
    from sklearn.linear_model import LinearRegression
    if len(x_) != len(y_) or len(x_) != len(z):
        raise ValueError("x_, y_, z 必须具有相同的长度。")

    X = np.vstack((x_, y_)).T
    model = LinearRegression()
    model.fit(X, z)
    a_, b_ = model.coef_
    c_ = model.intercept_

    normal_vector = np.array([a_, b_, -1])
    return a_, b_, c_, normal_vector


def vector_to_angles(normal_vector):
    """
    计算法向量与 X、Y、Z 轴的夹角（单位为度）。

    参数:
    - normal_vector: 长度为 3 的一维数组，法向量。

    返回:
    - angles: 一个字典，包含与 X、Y、Z 轴的夹角（单位为度）。
    """
    # 确保法向量为 NumPy 数组
    normal_vector = np.array(normal_vector)

    # 归一化法向量
    norm = np.linalg.norm(normal_vector)
    if norm == 0:
        raise ValueError("法向量长度为 0，无法计算角度。")
    unit_vector = normal_vector / norm

    # 坐标轴的单位向量
    x_axis = np.array([1, 0, 0])
    y_axis = np.array([0, 1, 0])
    z_axis = np.array([0, 0, 1])

    # 计算与各轴的夹角（弧度）
    angle_x = np.arccos(np.clip(np.dot(unit_vector, x_axis), -1.0, 1.0))
    angle_y = np.arccos(np.clip(np.dot(unit_vector, y_axis), -1.0, 1.0))
    angle_z = np.arccos(np.clip(np.dot(unit_vector, z_axis), -1.0, 1.0))

    # 转换为角度
    angles = {
        "angle_with_x": np.degrees(angle_x),
        "angle_with_y": np.degrees(angle_y),
        "angle_with_z": np.degrees(angle_z),
    }

    return angles


def rotate_data(data, normal_vector):
    """
    使用旋转矩阵将数据旋转，使法向量旋转到 Z 轴。

    参数:
    - data: 2D NumPy 数组，表示表面数据。
    - normal_vector: 法向量，形状为 (3,)。

    返回:
    - 旋转后的数据，形状与原数据相同。
    """
    # 确保目标向量为 Z 轴方向
    target_normal = np.array([0, 0, -1])

    # 计算旋转轴和旋转角度
    axis_of_rotation = np.cross(normal_vector, target_normal)  # 旋转轴
    norm_axis = np.linalg.norm(axis_of_rotation)

    # 如果法向量已经平行于 Z 轴，无需旋转
    if norm_axis == 0:
        return data

    # 归一化旋转轴
    axis_of_rotation = axis_of_rotation / norm_axis

    # 计算旋转角度（限制在合法范围 [-1, 1]）
    cos_theta = np.dot(normal_vector, target_normal) / (
            np.linalg.norm(normal_vector) * np.linalg.norm(target_normal)
    )
    angle_of_rotation = np.arccos(np.clip(cos_theta, -1.0, 1.0))

    # 使用旋转向量创建旋转矩阵
    rotation = R.from_rotvec(axis_of_rotation * angle_of_rotation)
    rotation_matrix = rotation.as_matrix()

    # 获取数据的坐标
    shape = data.shape
    x, y = np.meshgrid(np.arange(shape[1]), np.arange(shape[0]))
    coords = np.vstack([x.flatten(), y.flatten(), data.flatten()])

    # 旋转坐标
    rotated_coords = np.dot(rotation_matrix, coords)
    rotated_data = rotated_coords[2, :].reshape(shape)

    return rotated_data


def rotate_data2(data, normal_vector):
    from scipy.spatial.transform import Rotation as R
    """
    使用旋转矩阵旋转数据，将法向量旋转到 Z 轴
    """
    # 目标是将法向量 normal_vector 旋转到 Z 轴
    target_normal = np.array([0, 0, 0])  # Z轴方向
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


def flatten_surface_by_rotation(data, mask, media_z):
    """
    通过旋转数据使其接近平行的平面
    """
    data = np.copy(data)
    data[mask == False] = 0
    rows, cols = data.shape
    x, y = np.meshgrid(np.arange(cols), np.arange(rows))  # 获取X和Y的下标
    x = x.flatten()
    y = y.flatten()
    z = data.flatten()

    min_value = media_z - 3000  # 设置下限值
    max_value = media_z + 3000  # 设置上限值

    # 筛选出范围内的值
    non_zero_indices = np.logical_and(z > min_value, z < max_value)
    x = x[non_zero_indices]
    y = y[non_zero_indices]
    z = z[non_zero_indices]

    # 拟合平面并计算平面方程的系数
    a, b, c, normal_vector = fit_plane(x, y, z)
    angleData = vector_to_angles(normal_vector)
    print(f"拟合平面方程: z = {a}*x + {b}*y + {c} {normal_vector}")
    # 旋转数据使其法向量对齐到Z轴
    # rotated_data = rotate_data(data, np.array([a, b, 1]))
    return a, b, c, data, angleData


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
