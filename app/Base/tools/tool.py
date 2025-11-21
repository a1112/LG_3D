import cv2
import numpy
import numpy as np
from PIL import Image

from Base.property.Types import Point2D
from Base.utils.DetectionSpeedRecord import DetectionSpeedRecord
from Base.utils.Log import logger


def showImage(image, name="image"):

    if isinstance(image, Image.Image):
        image = np.array(image)
    cv2.namedWindow(name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(name, 800, 800)
    cv2.imshow(name, image)
    cv2.waitKey(0)


def getMask(gray_image):
    if isinstance(gray_image, Image.Image):
        gray_image = np.array(gray_image)

    blurred_image = cv2.GaussianBlur(gray_image, (9, 9), 0)

    # 应用阈值处理
    ret, binary_image = cv2.threshold(blurred_image, 30, 255, cv2.THRESH_BINARY)
    return binary_image


def get_foreground(gray_image, direction="L", key=None):
    if isinstance(gray_image, Image.Image):
        gray_image = np.array(gray_image)
    blurred_image = cv2.GaussianBlur(gray_image, (9, 9), 0)
    # 应用阈值处理
    _, binary_image = cv2.threshold(blurred_image, 65, 210, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    # ret, binary_image = cv2.threshold(blurred_image, 70, 255, cv2.THRESH_BINARY)
    # 应用形态学操作去除噪声
    kernel = np.ones((5, 5), np.uint8)  # 调整核的大小
    cleaned_image = cv2.morphologyEx(binary_image, cv2.MORPH_CLOSE, kernel, iterations=4)
    # cleaned_image=binary_image
    # 找到轮廓
    contours, _ = cv2.findContours(cleaned_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = list(contours)
    contours.sort(key=cv2.contourArea, reverse=True)
    print([cv2.contourArea(c) for c in contours])
    # 创建掩膜并填充最大的轮廓
    mask = np.zeros_like(gray_image)
    new_contours = []
    for c in contours:
        if direction == "L" or "D" in key or "M" in key:
            if cv2.boundingRect(c)[0] < 300:
                new_contours.append(c)
        elif direction == "R":

            if cv2.boundingRect(c)[0] + cv2.boundingRect(c)[2] > cleaned_image.shape[1] - 500:
                new_contours.append(c)
    if new_contours:
        largest_contour = max(new_contours, key=cv2.contourArea)
        rec2 = cv2.boundingRect(largest_contour)
        cv2.drawContours(mask, [largest_contour], -1, 255, thickness=cv2.FILLED)

    # 应用掩膜移除背景
    # foreground = cv2.bitwise_and(gray_image, gray_image, mask=mask)
    # return foreground, mask,rec
    return gray_image, mask


def auto_crop(key, image, star_pos, direction):
    gray_image, mask = get_foreground(image, direction, key)

    rec = crop_max_image_black_edges(key, mask, star_pos)
    x, y, w, h = rec
    return gray_image[y:y + h, x:x + w], mask[y:y + h, x:x + w], rec


def crop_max_image_black_edges(key, image, star_pos):
    # 图像列求和，检测哪些列是主要黑色的
    # column_sum = np.sum(gray, axis=0)
    h, w = image.shape
    column_no_black_count = np.sum(image > 100, axis=0)
    left_index = star_pos[0]
    right_index = w - star_pos[1]
    max_l = left_index + 300  # 规定最大裁剪
    min_r = right_index - 800  # 规定最大裁剪
    # 从左侧找到第一个非黑色列
    # l_threshold = 0.05 if "D" in key else 0.25
    # r_threshold = 0.25
    # while left_index > max_l or column_no_black_count[left_index]>5000*255: # /(column_no_black_count[max_l+100]) < l_threshold:
    #     left_index += 1
    l_limit = 10 if "S_D" in key else 500
    while True:
        if left_index > max_l:
            break
        if column_no_black_count[left_index] > l_limit:
            break
        left_index += 1

    # 从右侧找到第一个非黑色列
    # while right_index < maxR and column_no_black_count[right_index]>5*255: #/(column_no_black_count[maxR-100]) < r_threshold:
    #     right_index -= 1
    r_limit = 10 if "L_D" in key else 500
    while True:
        if right_index < min_r:
            break
        if column_no_black_count[right_index] > r_limit:
            break
        right_index -= 1
    logger.debug(f"r_index  {key}   {right_index}  {w-right_index} { column_no_black_count[right_index]}")
    # print(f"{key} {max_l} {maxR} left_index {left_index}  right_index {w-right_index}")
    # showImage(image)
    # 保存裁剪后的图像
    if "S_D" in key:
        x = left_index
    else:
        x = left_index+20

    if "L_D" in key:
        width = right_index - x
    else:
        width = right_index - x-20
    # print(f"裁剪 {key} {[x, 0, width, h]}")
    # tools.tool.showImage(image[:, x:x + width],f"{key}_{[x, 0, w-(width+x), h]}")
    return [x, 0, width, h]


def cropImage(image, cropLeft, cropRight):
    width, height = image.size
    left = cropLeft
    right = width - cropRight
    top = 0
    bottom = height
    image = image.crop((left, top, right, bottom))
    return image


def horizontal_projection_first_nonzero(mask):
    if isinstance(mask, Image.Image):
        mask = np.array(mask)
    # height = mask.shape[0]
    # 使用np.argmax找到第一个非零值的索引
    non_zero_indices = np.argmax(mask > 150, axis=0)
    # 处理整列都是零的情况
    # non_zero_indices[np.all(mask == 0, axis=0)] = height
    return non_zero_indices


def find_nearest(array, value):
    # 查找最接近的值的索引
    idx = np.searchsorted(array, value, side="left")
    if idx > 0 and (idx == len(array) or abs(value - array[idx - 1]) <= abs(value - array[idx])):
        return array[idx - 1], idx - 1
    else:
        return array[idx], idx


def getDiff(abs_diff, num=0):
    whereArray = np.where(abs_diff == num)
    if len(whereArray[0]) > 0:
        return list(whereArray[0])
    else:
        if num > 5:
            return []
        return getDiff(abs_diff, num + 1)


def find_cross_points(projections):
    cross_points = []
    # print("projections")
    # print(projections)
    # input()
    for i in range(1, len(projections)):
        l_ = projections[i - 1]
        r_ = projections[i]
        l_len = len(l_)
        abs_diff_l_r = np.abs(l_ - r_[0])
        f_l_List = getDiff(abs_diff_l_r, 0)
        if f_l_List:
            f_l_index = f_l_List[-1]
        else:
            f_l_index = l_len
        abs_diff_r_l = np.abs(r_ - l_[-1])
        f_r_list = getDiff(abs_diff_r_l, 0)
        if f_r_list:
            f_r_index = f_r_list[0]
        else:
            f_r_index = 0
        cross_points.append((int(l_len - f_l_index), int(f_r_index)))
    return cross_points


def crop_black_border(gray):
    if isinstance(gray, Image.Image):
        gray = np.array(gray)
    # 阈值处理，获得二值图像
    _, binary = cv2.threshold(gray, 1, 255, cv2.THRESH_BINARY)
    # 寻找非黑色区域的边界
    coords = cv2.findNonZero(binary)
    # 计算边界框
    x, y, w, h = cv2.boundingRect(coords)
    # 裁剪图像
    return x, y, w, h


def hstack_3d(npy_list, window_size=100, max_blocks=3, join_mask_image=None):
    """
    水平拼接多个 3D 高度矩阵，并对相邻块的边缘做高度对齐。

    Args:
        npy_list (List[np.ndarray]): 按顺序排列的 3D 高度矩阵。
        window_size (int): 连续多少行作为有效窗口判定。
        max_blocks (int): 边缘最多检测多少个有效窗口，取最后一个窗口的行号用于对齐。
        joinMaskImage (np.ndarray | None): 兼容旧接口，未使用。
        join_mask_image (np.ndarray | None): 兼容旧接口，未使用。

    Returns:
        np.ndarray: 拼接后的 3D 高度矩阵。
    """

    def find_valid_rows(column_data, ws, max_n, min_value=0):
        """在单列数据中查找连续 ws 行都大于 min_value 的起始行索引，最多返回 max_n 个。"""
        idxs = []
        total = len(column_data)
        for i in range(total // ws):
            start = i * ws
            end = start + ws
            if np.all(column_data[start:end] > min_value):
                idxs.append(start)
                if len(idxs) >= max_n:
                    break
        return idxs

    def edge_mean(data, start_row, width=3, side="left"):
        """计算指定行附近、左/右边缘若干列的均值。"""
        rows = slice(start_row, start_row + window_size)
        if side == "left":
            cols = data[rows, :width]
        else:
            cols = data[rows, -width:]
        valid = cols[cols > 1500]
        return np.mean(valid) if valid.size else np.nan

    stitched = [npy_list[0]]
    for idx in range(1, len(npy_list)):
        left = stitched[-1]
        right = npy_list[idx]

        r_left_col = right[:, 0]
        valid_rows = find_valid_rows(r_left_col, window_size, max_blocks, min_value=0)
        if not valid_rows:
            stitched.append(right)
            continue

        sample_row = valid_rows[-1]
        mean_l = edge_mean(left, sample_row, side="right")
        mean_r = edge_mean(right, sample_row, side="left")

        if np.isnan(mean_l) or np.isnan(mean_r) or abs(mean_l - mean_r) > 1e6:
            logger.error(f"hstack_3d align skip: mean_l={mean_l}, mean_r={mean_r}, row={sample_row}")
        else:
            right = right - mean_r + mean_l

        stitched.append(right)

    return np.hstack(stitched)


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

@DetectionSpeedRecord.timing_decorator("get_horizontal_projection_list")
def get_horizontal_projection_list(image_list):
    horizontal_projection_list = []
    for index, image in enumerate(image_list):  # 进行投影
        horizontal_projection = horizontal_projection_first_nonzero(image)
        horizontal_projection_list.append(horizontal_projection)
    return horizontal_projection_list


def hstack_3d(npy_list, window_size=100, max_blocks=3, join_mask_image=None):
    """
    水平拼接多个 3D 高度矩阵，并对相邻块的边缘做高度对齐。

    Args:
        npy_list (List[np.ndarray]): 需要拼接的 3D 高度矩阵列表，按顺序排列。
        window_size (int): 用于边缘检测的窗口高度（连续 window_size 行非零判定为有效区域）。
        max_blocks (int): 在边缘上最多检测多少个有效窗口，用最后一个窗口的行号来对齐。
        join_mask_image (np.ndarray | None): 未使用，保留接口。

    Returns:
        np.ndarray: 拼接后的 3D 高度矩阵。
    """

    def find_valid_rows(column_data, ws, max_n, min_value=0):
        """
        在单列数据中查找连续 ws 行都大于 min_value 的起始行索引，最多返回 max_n 个。
        """
        idxs = []
        total = len(column_data)
        for i in range(total // ws):
            start = i * ws
            end = start + ws
            if np.all(column_data[start:end] > min_value):
                idxs.append(start)
                if len(idxs) >= max_n:
                    break
        return idxs

    def edge_mean(data, start_row, width=3, side="left"):
        """
        计算指定行附近、左/右边缘若干列的均值，用于对齐。
        """
        if side == "left":
            cols = data[start_row:start_row + window_size, :width]
        else:
            cols = data[start_row:start_row + window_size, -width:]
        return np.mean(cols[cols > 1500]) if cols.size else np.nan

    stitched = [npy_list[0]]
    for idx in range(1, len(npy_list)):
        left = stitched[-1]
        right = npy_list[idx]

        # 取右块左边缘和左块右边缘
        r_left_col = right[:, 0]
        l_right_col = left[:, -1]

        # 找到右块左边缘的有效行窗口
        valid_rows = find_valid_rows(r_left_col, window_size, max_blocks, min_value=0)
        if not valid_rows:
            stitched.append(right)
            continue

        sample_row = valid_rows[-1]
        mean_l = edge_mean(left, sample_row, side="right")
        mean_r = edge_mean(right, sample_row, side="left")

        # 对齐：如果均值有效且差值合理，平移右块
        if np.isnan(mean_l) or np.isnan(mean_r) or abs(mean_l - mean_r) > 1e6:
            logger.error(f"hstack_3d align skip: mean_l={mean_l}, mean_r={mean_r}, row={sample_row}")
        else:
            right = right - mean_r + mean_l

        stitched.append(right)

    return np.hstack(stitched)


def get_circle_config_by_mask(mask):
    # 获取圆参数
    # showImage(mask)
    if isinstance(mask, Image.Image):
        mask = np.array(mask)
    mask = cv2.bitwise_not(mask)
    # 找到轮廓
    contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    image_center = (mask.shape[1] // 2, mask.shape[0] // 2)

    closest_contour = None
    min_distance = float('inf')

    for contour in contours:
        # 获取轮廓的外接矩形
        x, y, w, h = cv2.boundingRect(contour)
        # 计算矩形中心
        rect_center = (x + w // 2, y + h // 2)
        if h * w < (mask.shape[1] / 5) * (mask.shape[1] / 5):
            continue
        # 计算矩形中心与图像中心的距离
        distance = np.sqrt((rect_center[0] - image_center[0]) ** 2 + (rect_center[1] - image_center[1]) ** 2)
        # 找到最接近图像中心的轮廓
        if distance < min_distance:
            min_distance = distance
            closest_contour = contour
    (circlexX, circlexY), circlexRadius = cv2.minEnclosingCircle(closest_contour)
    rect = cv2.minAreaRect(closest_contour)
    (box_x, box_y), (box_w, box_h), box_angle = rect

    # 计算内接圆（在最小包围矩形中）
    inner_circle_radius = min(box_w, box_h) / 2
    inner_circle_center = (box_x, box_y)
    ellipse = cv2.fitEllipse(closest_contour)

    return {
        "inner_circle": {
            "circlex": [int(circlexX), int(circlexY), int(circlexRadius)],
            "ellipse": ellipse,
            "inner_circle": [inner_circle_center, inner_circle_radius]
        }
    }


def get_intersection_points(p1, p2, width, height):
    """
    获取两条线段的交点
    :return: 交点列表
    """
    x1, y1 = p1
    x2, y2 = p2

    intersection_points = []

    def add_point_if_on_boundary(x, y):
        if 0 <= x <= width and 0 <= y <= height:
            intersection_points.append(Point2D(int(x), int(y)))

    if x1 != x2 and y1 != y2:
        # 计算斜率和截距
        m = (y2 - y1) / (x2 - x1)
        c = y1 - m * x1

        # 求与上边界的交点 (y = 0)
        x_top = (0 - c) / m
        add_point_if_on_boundary(x_top, 0)

        # 求与下边界的交点 (y = height)
        x_bottom = (height - c) / m
        add_point_if_on_boundary(x_bottom, height)

        # 求与左边界的交点 (x = 0)
        y_left = m * 0 + c
        add_point_if_on_boundary(0, y_left)

        # 求与右边界的交点 (x = width)
        y_right = m * width + c
        add_point_if_on_boundary(width, y_right)
    elif x1 == x2:
        # 线垂直时，只会与上下边界相交
        add_point_if_on_boundary(x1, 0)
        add_point_if_on_boundary(x1, height)
    elif y1 == y2:
        # 线水平时，只会与左右边界相交
        add_point_if_on_boundary(0, y1)
        add_point_if_on_boundary(width, y1)
    for p in intersection_points:
        if p[0] < 0:
            p[0] = 0
        if p[1] < 0:
            p[1] = 0
        if p[0] >= width:
            p[0] = width - 1
        if p[1] >= height:
            p[1] = height - 1
    return intersection_points[:2]

def bound_box(box, image_size):
    """
    判断数组是否越界
    Args:
        box:
        image_size:

    Returns:

    """
    x,y,w,h = box
    width, height = image_size
    if x <0 or y < 0 or width <w+x or height< y+h:
        return True
    return False

def expansion_box(box, image_size, expand_factor=0.1,min_size=10,max_size=100):
    """
    扩展矩形框，使其尺寸增加一定比例，保持在图像尺寸内。

    参数:
    - box: 原始矩形框 (x, y, w, h)
    - image_size: 图像的尺寸 (width, height)
    - expand_factor: 扩展因子，控制扩展比例

    返回:
    - 扩展后的矩形框 (x, y, w, h)
    """
    x, y, w, h = box
    width, height = image_size

    # 计算扩展的尺寸
    if expand_factor==0:
        expand_w=0
        expand_h=0
    else:
        expand_w = max(min_size,min(max_size,w * expand_factor))
        expand_h = max(min_size,min(max_size,h * expand_factor))

    # 计算新的矩形位置和尺寸
    new_x = max(x - expand_w, 0)
    new_y = max(y - expand_h, 0)
    new_w = min(w + 2 * expand_w, width - new_x)
    new_h = min(h + 2 * expand_h, height - new_y)

    return int(new_x), int(new_y), int(new_w), int(new_h)
