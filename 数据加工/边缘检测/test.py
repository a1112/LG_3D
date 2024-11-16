import cv2
import numpy as np
import matplotlib.pyplot as plt

# 读取灰度图
  # 替换为你的灰度图路径



# 读取灰度图
image_path = fr'F:\datasets\LG_3D_DataBase\Data\S_M\1757\2d\9.bmp'
import cv2
import numpy as np
import matplotlib.pyplot as plt

# 读取图像
gray_image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)

# 应用阈值处理
_, binary_image = cv2.threshold(gray_image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

# 应用形态学操作去除噪声
kernel = np.ones((3, 3), np.uint8)
cleaned_image = cv2.morphologyEx(binary_image, cv2.MORPH_CLOSE, kernel, iterations=2)

# 找到轮廓
contours, _ = cv2.findContours(cleaned_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

# 创建掩膜并填充最大的轮廓
mask = np.zeros_like(gray_image)
if contours:
    largest_contour = max(contours, key=cv2.contourArea)
    cv2.drawContours(mask, [largest_contour], -1, 255, thickness=cv2.FILLED)

# 应用掩膜移除背景
foreground = cv2.bitwise_and(gray_image, gray_image, mask=mask)

# 显示结果
plt.figure(figsize=(10, 5))

plt.subplot(1, 3, 1)
plt.title('Original Image')
plt.imshow(gray_image, cmap='gray')

plt.subplot(1, 3, 2)
plt.title('Binary Image')
plt.imshow(binary_image, cmap='gray')

plt.subplot(1, 3, 3)
plt.title('Foreground')
plt.imshow(foreground, cmap='gray')

plt.show()
