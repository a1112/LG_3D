import cv2
import numpy
import numpy as np
from PIL import Image


def getMask(gray_image):
    if isinstance(gray_image, Image.Image):
        gray_image = np.array(gray_image)

    blurred_image = cv2.GaussianBlur(gray_image, (9, 9), 0)

    # 应用阈值处理
    ret, binary_image = cv2.threshold(blurred_image, 30, 255, cv2.THRESH_BINARY)
    return binary_image


def getForeground(gray_image,direction="L", key=None):
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
    newContours = []
    for c in contours:
        if direction == "L" or "D" in key or "M" in key:
            if cv2.boundingRect(c)[0] < 300:
                newContours.append(c)
        elif direction == "R":

            if cv2.boundingRect(c)[0]+cv2.boundingRect(c)[2] > cleaned_image.shape[1]-500:
                newContours.append(c)
    if newContours:
        largest_contour = max(newContours, key=cv2.contourArea)
        rec2 = cv2.boundingRect(largest_contour)
        cv2.drawContours(mask, [largest_contour], -1, 255, thickness=cv2.FILLED)

    # 应用掩膜移除背景
    # foreground = cv2.bitwise_and(gray_image, gray_image, mask=mask)
    # return foreground, mask,rec
    return gray_image, mask


def autoCrop(key, image,starPos,direction):
    gray_image, mask = getForeground(image,direction,key)

    rec = crop_max_image_black_edges(key, mask,starPos)
    x,y,w,h = rec
    return gray_image[y:y+h,x:x+w],mask[y:y+h,x:x+w],rec


def crop_max_image_black_edges(key,image, starPos):
    # 图像列求和，检测哪些列是主要黑色的
    # column_sum = np.sum(gray, axis=0)
    h,w = image.shape
    column_no_black_count = np.sum(image > 100, axis=0)
    left_index = starPos[0]
    right_index = w - starPos[1]
    maxL = left_index+150
    maxR = right_index-150
    # 从左侧找到第一个非黑色列
    l_threshold = 0.1 if "D" in key else 0.2
    r_threshold = 0.2

    while left_index < maxL and column_no_black_count[left_index]/(column_no_black_count[maxL]+1) < l_threshold:
        left_index += 1

    # 从右侧找到第一个非黑色列
    while right_index > maxR and column_no_black_count[right_index]/(column_no_black_count[maxR]+1) < r_threshold:
        right_index -= 1

    # 保存裁剪后的图像
    if "D" in key:
        x = left_index-15
    else:
        x = left_index+5
    r = right_index-5
    return [x,0,r-x,h]


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
    height = mask.shape[0]
    # 使用np.argmax找到第一个非零值的索引
    non_zero_indices = np.argmax(mask > 100, axis=0)
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
    for i in range(1, len(projections)):
        l_ = projections[i - 1]
        r_ = projections[i]
        abs_diff_l_r = np.abs(l_ - r_[0])
        f_l_List = getDiff(abs_diff_l_r, 0)
        if f_l_List:
            f_l_index = f_l_List[-1]
        else:
            f_l_index = len(l_)
        abs_diff_r_l = np.abs(r_ - l_[-1])
        f_r_list = getDiff(abs_diff_r_l, 0)
        if f_r_list:
            f_r_index = f_r_list[0]
        else:
            f_r_index = 0
        cross_points.append((int(f_l_index), int(f_r_index)))
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


def hstack3D(npyList,n_=100,num=10):

    def nZeeroIndexes(array,n, minValue=0):
        indices = []
        for i in range(len(array)//n):
            if np.all(array[i*n:(i+1) * n] > minValue):
                indices.append(i*n)
                if len(indices) > 3:
                    break
        return indices

    def getMean(data):
        data = data[data > 500]
        return numpy.mean(data)
    # 水平拼接3D图像
    for index in range(1, len(npyList)):
        r_npy = npyList[index]
        l_npy = npyList[index - 1]
        r_l_line = r_npy[:, 0]
        l_r_line = l_npy[:, -1]
        r_l_line_nz_indexes = nZeeroIndexes(r_l_line, n_, num)
        if r_l_line_nz_indexes:
            samplingIndex = r_l_line_nz_indexes[-1]
            meanL = getMean(l_npy[:, -5:-1][samplingIndex:samplingIndex+n_])
            meanR = getMean(r_npy[:, 1:5][samplingIndex:samplingIndex+n_])
            npyList[index] = npyList[index]-meanR+meanL
        else:
            pass
    return np.hstack(npyList)


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


def getHorizontalProjectionList(imageList):
    horizontalProjectionList = []
    for index, image in enumerate(imageList):  # 进行投影
        horizontalProjection = horizontal_projection_first_nonzero(image)
        horizontalProjectionList.append(horizontalProjection)
    return horizontalProjectionList


def getCircleConfigByMask(mask):
    # 获取圆参数
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
        if h*w<(mask.shape[1]/5)*(mask.shape[1]/5):
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
        "inner_circle":{
            "circlex":[int(circlexX), int(circlexY), int(circlexRadius)],
            "ellipse":ellipse,
            "inner_circle":[inner_circle_center, inner_circle_radius]
        }
    }
