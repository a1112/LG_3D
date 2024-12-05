import cv2
import glob
import numpy as np
import copy


def circle_flatten(np_data):
    # 获取图像最小边的长度，并将图像缩放为正方形
    size = min(np_data.shape[1], np_data.shape[0])
    np_data = cv2.resize(np_data, (size, size))

    # 计算图像中心点坐标
    x, y = np_data.shape[1] // 2, np_data.shape[0] // 2
    # 计算圆的最大半径
    r = min(np_data.shape[1] // 2, np_data.shape[0] // 2)

    # 计算展平后的条形圆环的宽和高
    height = int(r * 0.6)
    width = int(r * np.pi * 2)

    # 创建一个全零的矩阵作为结果容器
    rectangle = np.zeros([height, width])

    # 如果是三通道图像，创建三通道的矩阵
    if len(np_data.shape) == 3:
        rectangle = np.zeros([height, width, 3])

    print(rectangle.shape, np_data.shape)  # 输出矩阵尺寸

    # 遍历目标矩阵的每个像素位置
    for row in range(0, height):
        for col in range(0, width):
            # 转换为极坐标系
            theta = np.pi * 2.0 / height * (col + 1)
            rho = r - row - 1
            # 计算在原圆环中对应的像素坐标
            position_x = min(int(x + rho * np.cos(theta) + 0.5), np_data.shape[1] - 1)
            position_y = min(int(y - rho * np.sin(theta) + 0.5), np_data.shape[0] - 1)

            # 将原图像对应位置的值赋给展平后的矩阵
            rectangle[row, col] = np_data[position_y, position_x]

    return rectangle


def circle_flatten1(data):
    # 读取并转换为灰度图
    img = cv2.imread('images/circle_band.bmp')
    img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 使用霍夫圆变换检测圆
    circles = cv2.HoughCircles(img_gray, cv2.HOUGH_GRADIENT, 1, 50, param1=170, param2=100).squeeze()

    # 获取检测到的所有圆的半径
    circle_radius = circles[:, 2]
    # 获取最大半径的圆
    radius_biggest_index = np.argsort(circle_radius)[-1]

    print(radius_biggest_index)
    # 获取最大圆的信息
    circle = np.uint16(np.around(circles[radius_biggest_index]))

    # 在图像上绘制最大圆
    cv2.circle(img, (circle[0], circle[1]), radius=circle[2], color=(0, 0, 255), thickness=5)
    cv2.circle(img, (circle[0], circle[1]), radius=2, color=(255, 0, 0), thickness=2)

    # 计算展平后的条形圆环的宽和高
    height = int(circle_radius[radius_biggest_index] * np.pi * 2)
    width = int(circle_radius[radius_biggest_index] / 3)

    rectangle = np.zeros([width, height])

    print(rectangle.shape)
    print(img_gray.shape)

    # 遍历目标矩阵的每个像素位置
    for row in range(width):
        for col in range(height):
            # 转换为极坐标系
            theta = np.pi * 2.0 / height * (col + 1)
            rho = circle_radius[radius_biggest_index] - row - 1
            # 计算在原圆环中对应的像素坐标
            position_x = int(circle[0] + rho * np.cos(theta) + 0.5)
            position_y = int(circle[1] - rho * np.sin(theta) + 0.5)

            # 将原图像对应位置的值赋给展平后的矩阵
            rectangle[row, col] = img_gray[position_y, position_x]

    # 显示展平后的图像
    cv2.namedWindow("rectangle", 0)
    cv2.imshow("rectangle", rectangle)
    cv2.waitKey(0)


def merge_2d(path):
    # 用于合并多个2D图像
    part = None
    for file in glob.glob(path):
        img = cv2.imread(file, 0)  # 读取为灰度图
        if part is None:
            part = img
        else:
            part = np.vstack([part, img])  # 纵向拼接图像
    return part


def merge_3d(path):
    # 用于合并多个3D数据文件
    part = None
    for file in glob.glob(path):
        img = np.load(file)  # 加载3D数据文件
        if part is None:
            part = img
        else:
            part = np.vstack([part, img])  # 纵向拼接数据
    return -0.0135 * part  # 对数据进行缩放


def preprocess(data, S=True):
    # 数据预处理：旋转和翻转
    data = np.rot90(data, k=1, axes=(1, 0))  # 顺时针旋转90度
    if S is True:
        data = np.flipud(data)  # 上下翻转
    return data


def flat_surface_process(data, mask=None):
    '''
    用于将相机拍摄的目标进行调平处理，
    注意：此函数实现的前提是表面大部分区域为平面，要保证输入的数据是uint16数据直接乘以分辨率得到的，否则需要改变求模板的操作或直接外部输入mask
    '''
    dev_th = 100  # 去除z偏差超过这个范围的值
    sample_inv = 100  # 采样间隔
    h, w = data.shape[:2]

    if mask is None:
        mask = np.zeros(data.shape, np.uint8)
        # 求模板,第一步,去除为0的
        ind1 = np.argwhere(abs(data) >= 0.00001)
        if min(ind1.shape) > 0:
            mask[ind1[:, 0], ind1[:, 1]] = 1
            temp_med = np.median(data[ind1[:, 0], ind1[:, 1]])  # 获取非零部分的中位数
        else:
            temp_med = np.median(data)

        # 求模板,第2步,去除偏离平面较大的
        ind2 = np.argwhere(abs(data - temp_med) >= dev_th)
        if min(ind2.shape) > 0:
            mask[ind2[:, 0], ind2[:, 1]] = 0

    # 过滤干扰
    mask = get_max_contour(mask)

    # 采样并去除噪点
    xx, yy, zz = [], [], []
    for i in range(0, data.shape[0], sample_inv):
        for j in range(0, data.shape[1], sample_inv):
            if mask[i, j] > 0:
                xx.append(j)
                yy.append(i)
                zz.append(data[i, j])

    # 滤除噪点
    mean = np.mean(zz)
    std = np.std(zz)
    thres1 = mean + 2 * std
    thres2 = mean - 2 * std
    filterInd = [i for i in range(0, len(zz)) if thres2 < zz[i] < thres1]
    xx = [xx[i] for i in filterInd]
    yy = [yy[i] for i in filterInd]
    zz = [zz[i] for i in filterInd]

    xx, yy, zz = np.array(xx, np.float64), np.array(yy, np.float64), np.array(zz, np.float64)

    # 进行平面拟合
    A00, A11, A22 = np.sum(xx ** 2), np.sum(yy ** 2), zz.shape[0]
    A01 = A10 = np.sum(xx * yy)
    A02 = A20 = np.sum(xx)
    A12 = A21 = np.sum(yy)
    A = np.array([[A00, A01, A02],
                  [A10, A11, A12],
                  [A20, A21, A22]])

    B00 = np.sum(xx * zz)
    B10 = np.sum(yy * zz)
    B20 = np.sum(zz)
    B = np.array([[B00], [B10], [B20]])

    A_inv = np.linalg.inv(A)  # 求解A的逆矩阵
    M = np.dot(A_inv, B)  # 求平面拟合的参数

    # 计算平面拟合误差
    R = 0
    for i in range(0, len(xx)):
        R += np.abs(M[0] * xx[i] + M[1] * yy[i] + M[2] - zz[i])

    print('平面拟合误差：', R)

    return data - M[0] * xx - M[1] * yy - M[2]


def get_max_contour(data):
    # 提取图像的最大轮廓
    contours, _ = cv2.findContours(data, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if len(contours) == 0:
        return data
    contour = max(contours, key=cv2.contourArea)
    result = np.zeros_like(data)
    cv2.drawContours(result, [contour], -1, 255, thickness=cv2.FILLED)
    return result


def count_combin(part_U, part_M, part_D):
    # 用于统计三个部分的对齐情况，返回组合的偏移量
    # ... 省略部分代码，假设此函数对数据进行阈值化处理后返回合适的偏移量...
    pass


def combin_image(part_U, part_M, part_D, rept12, rept23):
    # 用于组合三个部分的图像
    # ... 省略部分代码...
    pass


def get_roi(data):
    # 获取图像的ROI区域
    _, thres = cv2.threshold(data, 127, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(thres, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # 找到最大轮廓
    max_contour = max(contours, key=cv2.contourArea)

    # 获取最大轮廓的外接矩形
    x, y, w, h = cv2.boundingRect(max_contour)

    return data[y:y + h, x:x + w]


def convert_to_flat_image_ing(img_3d, exp_f=10, th_3d=120):
    # 将3D图像转化为平面图像
    img_3d = flat_surface_process(img_3d)

    # 计算深度图
    diff = np.median(img_3d) - img_3d

    # 将深度图转换为颜色图
    img_2d = cloud_to_color_fast(diff, exp=exp_f)

    return img_2d


def cloud_to_color_fast(depth, exp=1, mode=0):
    # 将深度图转换为伪彩色图像
    depth = np.clip(depth, -exp, exp)
    img = cv2.applyColorMap(np.uint8(depth), cv2.COLORMAP_JET)
    return img


if __name__ == "__main__":
    # 运行展平圆环的函数
    data = cv2.imread("images/sample_image.png", cv2.IMREAD_GRAYSCALE)
    result = circle_flatten(data)
    cv2.imshow("Flattened Image", result)
    cv2.waitKey(0)
