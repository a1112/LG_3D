from tools.DataGet import DataGet
from PIL import Image
import io
from skimage.draw import line
from skimage.segmentation import find_boundaries
import numpy as np

dataGet = DataGet("image", "L", "1810", "MASK", False)
jpgBytes = dataGet.get_image()
mask_image = Image.open(io.BytesIO(jpgBytes))
npy_data = dataGet.get_3d_data()

mask_image = np.array(mask_image)
h, w = mask_image.shape

p1 = (0, 0)  # 起始点 (row, col)
p2 = (h - 1, w - 1)  # 终点 (row, col)


def extract_segment_values(npy_data, mask_image, p1, p2):
    # 使用 Bresenham's line algorithm 获取 p1 和 p2 之间的所有点
    rr, cc = line(p1[0], p1[1], p2[0], p2[1])

    # 找到 mask_image 的边界
    boundaries = find_boundaries(mask_image, mode='inner')

    # 筛选出与 mask_image 边界相交的点
    intersection_indices = np.where(boundaries[rr, cc])[0]
    if len(intersection_indices) < 2:
        print("No sufficient intersection points found on the boundary.")
        return []

    # 获取这些点的行列坐标
    intersection_rr = rr[intersection_indices]
    intersection_cc = cc[intersection_indices]
    # 初始化存储线段的列表
    lines = []
    # 提取每一对交点之间的线段值
    for i in range(0, len(intersection_rr) - 1, 2):
        # 获取当前和下一个交点
        pl = (intersection_rr[i], intersection_cc[i])
        pr = (intersection_rr[i + 1], intersection_cc[i + 1])
        # 使用 Bresenham's line algorithm 获取 pl 和 pr 之间的所有点
        segment_rr, segment_cc = line(pl[0], pl[1], pr[0], pr[1])
        # 从 npy 数据中提取这些点对应的值
        segment_values = npy_data[segment_rr, segment_cc]
        # 将这些点的坐标和对应的值组合在一起
        segment_points = list(zip(segment_rr, segment_cc, segment_values))
        lines.append(segment_points)

    return lines


segment_points = extract_segment_values(npy_data, mask_image, p1, p2)
