import cv2
import numpy as np
from pathlib import Path


def crop_black_edges(image_path, output_path):
    image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # 图像列求和，检测哪些列是主要黑色的
    # column_sum = np.sum(gray, axis=0)
    column_no_black_count = np.sum(gray > 30, axis=0)
    left_index = 0
    right_index = len(column_no_black_count) - 1

    # 从左侧找到第一个非黑色列
    while left_index < 200 and column_no_black_count[left_index]/column_no_black_count[200] < 0.1:
        left_index += 2

    # 从右侧找到第一个非黑色列
    while right_index > len(column_no_black_count)-200 and column_no_black_count[left_index]/column_no_black_count[-200] < 0.1:
        right_index -= 2

    # 裁剪图像
    cropped_image = image[:, left_index+15:right_index-15]

    # 保存裁剪后的图像
    cv2.imwrite(str(output_path), cropped_image)


# 示例用法
image_dir = Path(r'F:\ALG\SegTrainTest\trainTest\dataList\coilMask\Cap_S_M')
output_dir = Path(r'F:\ALG\SegTrainTest\trainTest\dataList\coilMask\Cap_S_M/cropped')
output_dir.mkdir(exist_ok=True, parents=True)

for file_name in image_dir.iterdir():
    if file_name.suffix in ['.jpg', '.png']:
        output_path = output_dir / file_name.name
        crop_black_edges(file_name, output_path)
