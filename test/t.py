import cv2
import numpy as np
image = cv2.imread('24.bmp')
from PIL import Image

# 读取 BMP 文件
image_path = '24.bmp'
img = Image.open(image_path)

# 将图像转换为 numpy 数组
img_array = np.array(img)

# 获取图像的原始形状
original_shape = img_array.shape[::-1]

# 将 numpy 数组展平成一维数组
flat_array = img_array.flatten()

# 将一维数组 reshape 为原始形状
reshaped_array = flat_array.reshape(original_shape)

# 打印结果进行验证
print(f"Original shape: {original_shape}")
print(f"Flat array shape: {flat_array.shape}")
print(f"Reshaped array shape: {reshaped_array.shape}")
Image.fromarray(reshaped_array).save("test.bmp")