from typing import List

from CoilDataBase.models import AlarmFlatRoll
from PIL import Image
import cv2
import numpy as np
from property.Base import DataIntegration


class AlarmFlatRollItemData:
    def __init__(self):
        pass


class CircleDataItem:
    def __init__(self, data):
        self.data = data
        self.circle = data["circle"]
        self.ellipse = data["ellipse"]
        self.inner_circle = data["inner_circle"]


def contour_to_data(contour):
    (circlexX, circlexY), circlexRadius = cv2.minEnclosingCircle(contour)
    rect = cv2.minAreaRect(contour)
    (box_x, box_y), (box_w, box_h), box_angle = rect
    # 计算内接圆（在最小包围矩形中）
    inner_circle_radius = min(box_w, box_h) / 2
    inner_circle_center = (box_x, box_y)
    ellipse = cv2.fitEllipse(contour)
    return CircleDataItem({
        "circle":[int(circlexX), int(circlexY), int(circlexRadius)],
        "ellipse":ellipse,
        "inner_circle":[inner_circle_center, inner_circle_radius]
    })

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
    return contour_to_data(closest_contour)

def get_circle_contour(mask):
    contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    max_contour = max(contours, key=cv2.contourArea)
    return contour_to_data(max_contour)

def get_data(mask):
    return get_circle_contour(mask), get_inner_circle_contour(mask)



def _detectionAlarmFlatRoll_(dataIntegration: DataIntegration):
    mask = dataIntegration.npy_mask
    print(mask)
    circle_data_out,circle_data_in = get_data(mask)
    accuracy_x=dataIntegration.scan3dCoordinateScaleX
    accuracy_y=dataIntegration.scan3dCoordinateScaleX
    level=1
    errorStr = ""
    alarmFlat_Roll = AlarmFlatRoll(
        secondaryCoilId=dataIntegration.coilId,
        surface=dataIntegration.key,
        out_circle_width=circle_data_out.ellipse[1][0] * accuracy_x,
        out_circle_height=circle_data_out.ellipse[1][1] * accuracy_x,
        out_circle_center_x=circle_data_out.ellipse[0][0] * accuracy_x,
        out_circle_center_y=circle_data_out.ellipse[0][1] * accuracy_x,
        out_circle_radius=circle_data_out.ellipse[2] * accuracy_x,
        inner_circle_width=circle_data_in.ellipse[1][0] * accuracy_x,
        inner_circle_height=circle_data_in.ellipse[1][1] * accuracy_x,
        inner_circle_center_x=circle_data_in.ellipse[0][0] * accuracy_x,
        inner_circle_center_y=circle_data_in.ellipse[0][1] * accuracy_x,
        inner_circle_radius=circle_data_in.ellipse[2] * accuracy_x,
        accuracy_x=accuracy_x,
        accuracy_y=accuracy_y,
        level=level,
        err_msg=errorStr
    )
    dataIntegration.alarmFlat_Roll = alarmFlat_Roll

def _detectionAlarmFlatRollAll_(dataIntegrationList: List[DataIntegration]):
    for dataIntegration in dataIntegrationList:
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





