import numpy as np
from PIL import Image

# 读取 numpy 数组文件（假设文件名为 'data.npy'）
data = np.fromfile('1.bin', dtype=np.uint16)
data=data.reshape((1024,2560))
print(data)
# 检查数据类型
print(f"Original data type: {data.dtype}")

# 数据可能是 uint16，需要将其转换为 uint8
# 这可能需要一些缩放操作，确保数据在 0-255 范围内
# 如果数据范围本来就在 0-255，则可以直接转换
if data.dtype == np.uint16:
    data = (data / 256).astype(np.uint8)

# 检查转换后的数据类型
print(f"Converted data type: {data.dtype}")

# 将 numpy 数组转换为图像
img = Image.fromarray(data)
print(img)
# 保存图像为 BMP 文件
output_path = 'output_image.bmp'
img.save(output_path)

print(f"Image saved to {output_path}")