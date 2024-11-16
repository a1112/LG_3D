import numpy as np
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression


def rotate_around_x_axis(height_data, angle):
    """
    旋转二维高度数据围绕X轴旋转，保持原来的宽高

    参数:
    height_data (numpy.ndarray): 二维高度数据
    angle (float): 旋转角度（以度为单位）

    返回:
    numpy.ndarray: 旋转后的高度数据
    """
    rows, cols = height_data.shape
    x = np.arange(cols)
    y = np.arange(rows)
    xx, yy = np.meshgrid(x, y)

    # 构建绕X轴的旋转矩阵
    angle_rad = np.radians(angle)
    Rx = np.array([[1, 0, 0],
                   [0, np.cos(angle_rad), -np.sin(angle_rad)],
                   [0, np.sin(angle_rad), np.cos(angle_rad)]])

    # 应用旋转矩阵
    points = np.vstack((xx.ravel(), yy.ravel(), height_data.ravel())).T
    rotated_points = np.dot(points, Rx.T)

    # 将旋转后的点转换回二维高度数据
    rotated_height_data = rotated_points[:, 2].reshape(height_data.shape)

    return rotated_height_data


def generate_sample_data(rows, cols):
    """
    生成示例高度数据
    """
    np.random.seed(42)
    x = np.linspace(0, 10, cols)
    y = np.linspace(0, 10, rows)
    xx, yy = np.meshgrid(x, y)
    zz = 0.5 * yy + np.random.normal(0, 0.1, (rows, cols))
    return zz


def calculate_tilt_angle(height_data):
    """
    计算倾斜角度
    """
    y = np.arange(height_data.shape[0])
    yy = np.repeat(y, height_data.shape[1]).reshape(-1, 1)
    z = height_data.ravel()

    # 线性回归拟合线
    model = LinearRegression()
    model.fit(yy, z)
    b = model.coef_[0]

    # 计算倾斜角度
    tilt_angle = np.degrees(np.arctan(b))
    return tilt_angle


# 生成示例数据
rows, cols = 100, 100
height_data = generate_sample_data(rows, cols)

# 计算倾斜角度
tilt_angle = calculate_tilt_angle(height_data)
print(f"倾斜角度: Y方向 {tilt_angle:.2f} 度")

# 修正倾斜
corrected_height_data = rotate_around_x_axis(height_data, -tilt_angle)
print(corrected_height_data.shape)

#
# # 可视化修正前后的数据
# fig = plt.figure(figsize=(14, 6))
#
# # 原始数据
# ax1 = fig.add_subplot(121, projection='3d')
# x = np.arange(cols)
# y = np.arange(rows)
# xx, yy = np.meshgrid(x, y)
# ax1.plot_surface(xx, yy, height_data, cmap='viridis')
# ax1.set_title('Original Data')
# ax1.set_xlabel('X')
# ax1.set_ylabel('Y')
# ax1.set_zlabel('Height')
#
# # 修正后的数据
# ax2 = fig.add_subplot(122, projection='3d')
# ax2.plot_surface(xx, yy, corrected_height_data, cmap='viridis')
# ax2.set_title('Corrected Data')
# ax2.set_xlabel('X')
# ax2.set_ylabel('Y')
# ax2.set_zlabel('Height')
#
# plt.show()
