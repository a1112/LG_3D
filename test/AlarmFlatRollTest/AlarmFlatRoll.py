from PIL import Image
import cv2
import numpy as np
def contour_to_data(contour):
    (circlexX, circlexY), circlexRadius = cv2.minEnclosingCircle(contour)
    rect = cv2.minAreaRect(contour)
    (box_x, box_y), (box_w, box_h), box_angle = rect

    # 计算内接圆（在最小包围矩形中）
    inner_circle_radius = min(box_w, box_h) / 2
    inner_circle_center = (box_x, box_y)
    ellipse = cv2.fitEllipse(contour)
    return {
        "inner_circle":{
            "circlex":[int(circlexX), int(circlexY), int(circlexRadius)],
            "ellipse":ellipse,
            "inner_circle":[inner_circle_center, inner_circle_radius]
        }
    }

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





