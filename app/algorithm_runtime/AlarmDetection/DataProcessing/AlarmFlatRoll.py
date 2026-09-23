from typing import Union

from CoilDataBase import Alarm
from PIL import Image
import cv2
import numpy as np
from Base.property.Base import DataIntegration, DataIntegrationList
from Base.property.detection3D.FlatRollData import CircleDataItem
from Base.tools import tool
from Base.utils.Log import logger
from AlarmDetection.Result.FlatRollData import FlatRollData
from AlarmDetection.Result.errors import record_alarm_error


def _binary_mask(mask):
    source = np.asarray(mask)
    if source.ndim != 2 or source.size == 0:
        raise ValueError("coil mask must be a non-empty 2D array")
    if not (np.issubdtype(source.dtype, np.number)
            or np.issubdtype(source.dtype, np.bool_)) or np.iscomplexobj(source):
        raise ValueError("coil mask must contain numeric values")
    return np.where(np.isfinite(source) & (source > 0), 255, 0).astype(np.uint8)


def contour_to_data(contour, key):
    if contour is None:
        raise ValueError(f"{key} contour is missing")
    contour = np.asarray(contour)
    if contour.ndim < 2 or len(contour) < 3:
        raise ValueError(f"{key} contour has insufficient points")
    # 计算外接圆
    (circlex_x, circlex_y), circlex_radius = cv2.minEnclosingCircle(contour)
    rect = cv2.minAreaRect(contour)
    (box_x, box_y), (box_w, box_h), box_angle = rect
    if min(box_w, box_h) <= 0:
        raise ValueError(f"{key} contour is degenerate")
    # 计算内接圆（在最小包围矩形中）
    inner_circle_radius = min(box_w, box_h) / 2
    # fitEllipse requires at least five points and can fail for a degenerate
    # contour.  Keep a deterministic rectangle based fallback so a noisy mask
    # does not crash the whole alarm pipeline.
    if len(contour) >= 5:
        try:
            ellipse = cv2.fitEllipse(contour)
        except cv2.error:
            ellipse = ((float(box_x), float(box_y)),
                       (float(box_w), float(box_h)), float(box_angle))
    else:
        ellipse = ((float(box_x), float(box_y)),
                   (float(box_w), float(box_h)), float(box_angle))
    return CircleDataItem({
        "circle": [int(circlex_x), int(circlex_y), int(circlex_radius)],
        "ellipse": ellipse,
        "inner_circle": [box_x, box_y, inner_circle_radius]
    }, key)


def get_inner_circle_contour(mask):
    mask = _binary_mask(mask)
    recovered_ellipse = tool.get_inner_ellipse_by_mask(mask)
    if recovered_ellipse is not None:
        center_x, center_y = (int(round(value)) for value in recovered_ellipse[0])
        if not (0 <= center_y < mask.shape[0] and 0 <= center_x < mask.shape[1]) or mask[center_y, center_x] > 0:
            recovered_ellipse = None
    if recovered_ellipse is not None:
        (center_x, center_y), (ellipse_width,
                               ellipse_height), _ = recovered_ellipse
        return CircleDataItem({
            "circle": [
                int(center_x),
                int(center_y),
                int(max(ellipse_width, ellipse_height) / 2),
            ],
            "ellipse": recovered_ellipse,
            "inner_circle": [
                center_x,
                center_y,
                min(ellipse_width, ellipse_height) / 2,
            ],
        }, "in")
    # 获取内圆轮廓
    mask = cv2.bitwise_not(mask)
    # 找到轮廓
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    image_center = (mask.shape[1] // 2, mask.shape[0] // 2)
    closest_contour = None
    min_distance = float('inf')
    for contour in contours:
        # 获取轮廓的外接矩形
        x, y, w, h = cv2.boundingRect(contour)
        # The inverted image border is background, never the coil eye.
        if x == 0 or y == 0 or x + w >= mask.shape[1] or y + h >= mask.shape[0]:
            continue
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
    if closest_contour is None:
        raise ValueError("inner circle contour is missing")
    return contour_to_data(closest_contour, "in")


def get_circle_contour(mask):
    mask = _binary_mask(mask)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        raise ValueError("outer circle contour is missing")
    max_contour = max(contours, key=cv2.contourArea)
    return contour_to_data(max_contour, "out")


def get_data(mask):
    return get_circle_contour(mask), get_inner_circle_contour(mask)


def _detectionAlarmFlatRoll_(data_integration: DataIntegration):
    data_integration.alarmData.set_flat_roll_data(None)
    data_integration.alarmData.flat_roll_error = ""
    data_integration.alarmData.flat_roll_grad_result = None
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
    logger.debug("AlarmFlatRollAll")
    for dataIntegration in data_integration_list:
        try:
            _detectionAlarmFlatRoll_(dataIntegration)
        except (ValueError, TypeError, AttributeError, cv2.error) as e:
            dataIntegration.alarmData.flat_roll_error = str(e)
            record_alarm_error(dataIntegration, "flat_roll", e)
            logger.warning("flat roll detection failed coil=%s surface=%s: %s",
                           getattr(dataIntegration, "coilId", ""),
                           getattr(dataIntegration, "surface", ""), e)


if __name__ == "__main__":
    # 读取 png 文件
    image_path = 'test.png'
    img = Image.open(image_path)
    # 外切圆
    # 将图像转换为 numpy 数组
    img_array = np.array(img)
    circle_config = get_circle_contour(img_array)
    logger.info(circle_config)
    inner_circle_config = get_inner_circle_contour(img_array)
    logger.info(inner_circle_config)
