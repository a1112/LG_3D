import cv2
import numpy as np
import matplotlib.pyplot as plt

# 读取二值化的环形 mask 图像
mask = cv2.imread(r'F:\datasets\LG_3D_DataBase\DataSave\surface_L\1700\MASK.png', cv2.IMREAD_GRAYSCALE)
mask = cv2.bitwise_not(mask)
# 找到轮廓
contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

# 假设内圆是第一个轮廓（需要根据实际情况调整）
inner_circle_contour = contours[2]
# print(contours)
# 计算最小外接圆
(x, y), radius = cv2.minEnclosingCircle(inner_circle_contour)

# 绘制结果
output_image = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
cv2.circle(output_image, (int(x), int(y)), int(radius), (255, 0, 0), 5)

ellipse = cv2.fitEllipse(inner_circle_contour)

(x_inner, y_inner), radius_inner = cv2.minEnclosingCircle(inner_circle_contour)

# 计算外切圆
(x_outer, y_outer), radius_outer = cv2.minEnclosingCircle(inner_circle_contour)

rect = cv2.minAreaRect(inner_circle_contour)
(box_x, box_y), (box_w, box_h), box_angle = rect

# 计算内接圆（在最小包围矩形中）
inner_circle_radius = min(box_w, box_h) / 2
inner_circle_center = (box_x, box_y)

# 绘制结果

cv2.ellipse(output_image, ellipse, (255, 0, 0), 5)

print((x, y), radius)

print(ellipse)

(center, axes, angle) = ellipse
(major_axis, minor_axis) = axes

# 计算压缩比率
compression_ratio = minor_axis / major_axis

# 打印椭圆参数
print(f"椭圆中心: {center}")
print(f"长轴长度: {major_axis}")
print(f"短轴长度: {minor_axis}")
print(f"压缩比率: {compression_ratio:.4f}")

# 显示图像
plt.imshow(output_image)
plt.show()


