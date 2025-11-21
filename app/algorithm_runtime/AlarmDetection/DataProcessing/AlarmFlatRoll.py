from typing import Union

from CoilDataBase import Alarm
from PIL import Image
import cv2
import numpy as np
from Base.property.Base import DataIntegration, DataIntegrationList
from Base.property.detection3D.FlatRollData import CircleDataItem
from AlarmDetection.Result.FlatRollData import FlatRollData


def contour_to_data(contour, key):
    # 计算外接圆
    (circlex_x, circlex_y), circlex_radius = cv2.minEnclosingCircle(contour)
    rect = cv2.minAreaRect(contour)
    (box_x, box_y), (box_w, box_h), box_angle = rect
    # 计算内接圆（在最小包围矩形中）
    inner_circle_radius = min(box_w, box_h) / 2
    ellipse = cv2.fitEllipse(contour)
    return CircleDataItem({
        "circle": [int(circlex_x), int(circlex_y), int(circlex_radius)],
        "ellipse": ellipse,
        "inner_circle": [box_x, box_y, inner_circle_radius]
    }, key)


def get_inner_circle_contour(mask):
    # 获取内圆轮廓
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
    return contour_to_data(closest_contour, "in")


def get_circle_contour(mask):
    contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    max_contour = max(contours, key=cv2.contourArea)
    return contour_to_data(max_contour, "out")


def get_data(mask):
    return get_circle_contour(mask), get_inner_circle_contour(mask)


def _detectionAlarmFlatRoll_(data_integration: DataIntegration):
    mask = data_integration.npy_mask
    circle_data_out, circle_data_in = get_data(mask)
    flat_roll_data = FlatRollData(data_integration, circle_data_in, circle_data_out)
    data_integration.alarmData.set_flat_roll_data(flat_roll_data)
    return flat_roll_data


def commitData(data_integration: DataIntegration, flat_roll_data):
    Alarm.addObj(flat_roll_data.get_alarm_flat_roll(data_integration))


def _detectionAlarmFlatRollAll_(data_integration_list: Union[DataIntegrationList, DataIntegration]):
    """
    全局检测 扁卷
    """
    print("AlarmFlatRollAll")
    for dataIntegration in data_integration_list:
        _detectionAlarmFlatRoll_(dataIntegration)


if __name__ == "__main__":
    # 读取 png 文件
    image_path = 'test.png'
    img = Image.open(image_path)
    # 外切圆
    # 将图像转换为 numpy 数组
    img_array = np.array(img)
    circle_config = get_circle_contour(img_array)
    print(circle_config)
    inner_circle_config = get_inner_circle_contour(img_array)
    print(inner_circle_config)
