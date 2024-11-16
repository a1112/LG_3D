# from api.DataGet import DataGet
# from PIL import Image
# import io
from skimage.draw import line
# from skimage.segmentation import find_boundaries
import numpy as np


def get_intersection_points(p1, p2, width, height):
    x1, y1 = p1
    x2, y2 = p2
    print(p1,p2,width,height)
    intersection_points = []

    def add_point_if_on_boundary(x, y):
        if 0 <= x <= width and 0 <= y <= height:
            intersection_points.append([x, y])

    if x1 != x2 and y1 != y2:
        # 计算斜率和截距
        m = (y2 - y1) / (x2 - x1)
        c = y1 - m * x1

        # 求与上边界的交点 (y = 0)
        x_top = (0 - c) / m
        add_point_if_on_boundary(x_top, 0)

        # 求与下边界的交点 (y = height)
        x_bottom = (height - c) / m
        add_point_if_on_boundary(x_bottom, height)

        # 求与左边界的交点 (x = 0)
        y_left = m * 0 + c
        add_point_if_on_boundary(0, y_left)

        # 求与右边界的交点 (x = width)
        y_right = m * width + c
        add_point_if_on_boundary(width, y_right)
    elif x1 == x2:
        # 线垂直时，只会与上下边界相交
        add_point_if_on_boundary(x1, 0)
        add_point_if_on_boundary(x1, height)
    elif y1 == y2:
        # 线水平时，只会与左右边界相交
        add_point_if_on_boundary(0, y1)
        add_point_if_on_boundary(width, y1)
    for p in intersection_points:
        if p[0] < 0:
            p[0] = 0
        if p[1] < 0:
            p[1] = 0
        if p[0] >= width:
            p[0] = width - 1
        if p[1] >= height:
            p[1] = height - 1
    return intersection_points


def extract_segment_values(npy_data, mask_image, p1, p2):
    # 使用 Bresenham's line algorithm 获取 p1 和 p2 之间的所有点
    h,w = mask_image.shape

    p1,p2 = get_intersection_points(p1,p2,w,h)
    p1 = [int(p1[0]),int(p1[1])]
    p2 = [int(p2[0]),int(p2[1])]
    print(p1,p2)
    rr, cc = line(p1[0], p1[1], p2[0], p2[1])
    # 找到 mask_image 的边界
    # boundaries = find_boundaries(mask_image, mode='inner')
    # 筛选出与 mask_image 边界相交的点
    # intersection_indices = np.where(boundaries[cc, rr])[0]
    # if len(intersection_indices) < 2:
    #     print("No sufficient intersection points found on the boundary.")
    #     return []

    # 获取这些点的行列坐标
    intersection_rr = []
    intersection_cc = []
    mask_image[cc[0], rr[0]] = 0
    mask_image[cc[-1], rr[-1]] = 0
    hasSteel = False
    for r,z in zip(rr,cc):
        if mask_image[z,r] > 100 and not hasSteel:
            intersection_rr.append(r)
            intersection_cc.append(z)
            hasSteel = True
        elif mask_image[z,r] < 100 and hasSteel:
            intersection_rr.append(r)
            intersection_cc.append(z)
            hasSteel = False
    # 初始化存储线段的列表
    lines = []
    # 提取每一对交点之间的线段值
    for i in range(0, len(intersection_rr) - 1, 2):
        # 获取当前和下一个交点
        pl = (intersection_rr[i], intersection_cc[i])
        pr = (intersection_rr[i + 1], intersection_cc[i + 1])
        print(pl,pr)
        # 使用 Bresenham's line algorithm 获取 pl 和 pr 之间的所有点
        segment_rr, segment_cc = line(pl[0], pl[1], pr[0], pr[1])
        # 从 npy 数据中提取这些点对应的值
        segment_values = npy_data[segment_cc,segment_rr]
        # 将这些点的坐标和对应的值组合在一起
        segment_points = list(zip(list(segment_rr.tolist()), list(segment_cc.tolist()),list(segment_values.tolist())))
        if len(segment_points) > 100:
            lines.append({
                "len": len(segment_points),
                "points": segment_points,
                "pointL": [int(pl[0]), int(pl[1])],
                "pointR": [int(pr[0]), int(pr[1])],
                "min":int(np.min(segment_values)),
                "max":int(np.max(segment_values)),
                "mean":int(np.mean(segment_values)),
                "std":int(np.std(segment_values)),
                "median":int(np.median(segment_values)),
            })

    return lines


def getLengthData(npy_data, mask_image, p1, p2):
    p1 = [int(p1[0]),int(p1[1])]
    p2 = [int(p2[0]),int(p2[1])]
    segment_points = extract_segment_values(npy_data, mask_image, p1, p2)
    return segment_points
