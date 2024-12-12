# from api.DataGet import DataGet
# from PIL import Image
# import io
from skimage.draw import line
# from skimage.segmentation import find_boundaries
import numpy as np

from property.Types import Point2D
from property.Data3D import LineData
from tools.tool import get_intersection_points


def extract_segment_values(npy_data, mask_image, p1, p2):
    # 使用 Bresenham's line algorithm 获取 p1 和 p2 之间的所有点
    lineData = LineData(npy_data, mask_image, p1, p2)
    h, w = mask_image.shape

    p1, p2 = get_intersection_points(p1, p2, w, h)
    p1 = [int(p1[0]), int(p1[1])]
    p2 = [int(p2[0]), int(p2[1])]
    rr, cc = line(p1[0], p1[1], p2[0], p2[1])
    print(rr, cc)
    return lineData
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
    for r, z in zip(rr, cc):
        if mask_image[z, r] > 100 and not hasSteel:
            intersection_rr.append(r)
            intersection_cc.append(z)
            hasSteel = True
        elif mask_image[z, r] < 100 and hasSteel:
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
        # 使用 Bresenham's line algorithm 获取 pl 和 pr 之间的所有点
        segment_rr, segment_cc = line(pl[0], pl[1], pr[0], pr[1])
        # 从 npy 数据中提取这些点对应的值
        segment_values = npy_data[segment_cc, segment_rr]
        # 将这些点的坐标和对应的值组合在一起
        segment_points = list(zip(list(segment_rr.tolist()), list(segment_cc.tolist()), list(segment_values.tolist())))
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


def getP2ByRotate(p1, rotate, length=1000):
    """
    通过旋转角度和长度，计算从点 p1 得到的新点 p2。

    :param p1: 起始点 (x1, y1)
    :param rotate: 旋转角度 (弧度制)
    :param length: 旋转后新点与 p1 的距离 (默认值: 1000)
    :return: 新点 p2 (Point2D)
    """
    # 使用旋转公式计算新的点
    x2 = p1[0] + np.cos(rotate) * length
    y2 = p1[1] + np.sin(rotate) * length

    # 创建并返回新点
    return Point2D(x2, y2)


def getLengthDataByPoints(npy_data, mask_image, p1, p2, ray=False):
    p1 = Point2D(int(p1[0]), int(p1[1]))
    p2 = Point2D(int(p2[0]), int(p2[1]))
    # segment_points = extract_segment_values(npy_data, mask_image, p1, p2)
    lineData = LineData(npy_data, mask_image, p1, p2)
    # print(len(list(lineData.mask_image_line_points())))
    # input("pause")
    # if ray: # 射线模式,只对线段进行判断
    #     def directionEqual(direction1, direction2): # 计算两个方向是否相等
    #         return direction1[0] == direction2[0] and direction1[1] == direction2[1]
    #     direction = (p2[0] - p1[0], p2[1] - p1[1] )
    #     segment_points = [l for l in segment_points if directionEqual(direction, (l["points"][0][0]-p1[0], l["points"][0][1]-p1[1]))]

    return lineData


def getLengthDataByRotate(npy_data, mask_image, p1, rotate, ray=False):
    rotate = np.pi / 180 * rotate
    p2 = getP2ByRotate(p1, rotate)
    return getLengthDataByPoints(npy_data, mask_image, p1, p2, ray)


def getLengthData(npy_data, mask_image, p1, p2, ray=False):
    return getLengthDataByPoints(npy_data, mask_image, p1, p2, ray)


def auto_data_leveling_3d(data, mask_src):
    """
    自动数据配平
    Returns:

    """

    dev_th = 100  # 去除z偏差超过这个范围的值
    sample_inv = 100  # 采样间隔
    h, w = data.shape[:2]
    ind = np.argwhere(abs(data) <= 0.00001)
    if mask_src is None:
        mask = np.zeros(data.shape, np.uint8)
        # 求模板,第一步,去除为0的
        ind1 = np.argwhere(abs(data) >= 0.00001)
        if min(ind1.shape) > 0:
            mask[ind1[:, 0], ind1[:, 1]] = 1
            temp_med = np.median(data[ind1[:, 0], ind1[:, 1]])
        else:
            temp_med = np.median(data)
        # 求模板,第2步,去除偏离平面较大的
        ind2 = np.argwhere(abs(data - temp_med) >= dev_th)
        if min(ind2.shape) > 0:
            mask[ind2[:, 0], ind2[:, 1]] = 0
        # mask = get_max_contour(mask)
    else:
        mask_z = np.zeros(data.shape, np.uint8)
        mask_o = np.ones(data.shape, np.uint8)
        mask = np.where(abs(mask_src)>0.5, mask_o, mask_z)
    # 过滤干扰
    # import  cv2
    # cv2.namedWindow("mask", 0)
    # cv2.imshow("mask", mask*128)
    # cv2.waitKey(0)
    # 调平来去除旋转干扰, 限制一定范围
    xx, yy, zz = [], [], []
    for i in range(0, data.shape[0], sample_inv):
        for j in range(0, data.shape[1], sample_inv):
            if mask[i, j] > 0:
                xx.append(j)
                yy.append(i)
                zz.append(data[i, j])
    # 滤除可能的噪点
    mean = np.mean(zz)
    std = np.std(zz)
    thres1 = mean + 0.5 * std
    thres2 = mean - 0.5 * std
    filterInd = [i for i in range(0, len(zz)) if thres2 < zz[i] < thres1]

    xx = [xx[i] for i in filterInd]
    yy = [yy[i] for i in filterInd]
    zz = [zz[i] for i in filterInd]
    #
    xx, yy, zz = np.array(xx, np.float64), np.array(yy, np.float64), np.array(zz, np.float64)

    A00, A11, A22 = np.sum(xx ** 2), np.sum(yy ** 2), zz.shape[0]
    A01 = A10 = np.sum(xx * yy)
    A02 = A20 = np.sum(xx)
    A12 = A21 = np.sum(yy)
    A = np.array([[A00, A01, A02],
                  [A10, A11, A12],
                  [A20, A21, A22]])
    B00 = np.sum(xx * zz)
    B10 = np.sum(yy * zz)
    B20 = np.sum(zz)
    B = np.array([[B00], [B10], [B20]])
    A_inv = np.linalg.inv(A)
    M = np.dot(A_inv, B)

    bCountErr = True
    if bCountErr is True:
        R = 0
        for i in range(0, zz.shape[0]):
            R = R + (M[0, 0] * xx[i] + M[1, 0] * yy[i] + M[2, 0] - zz[i]) ** 2
        print("平面拟合误差为：", R)
    # 各数据点坐标到直线的距离
    X = np.linspace(0, w, w)
    X = X[np.newaxis, :]
    X_New = np.repeat(X, h, axis=0)

    Y = np.linspace(0, h, h)
    Y = Y[:, np.newaxis]
    Y_New = np.repeat(Y, w, axis=1)

    Temp = (M[0, 0] * X_New + M[1, 0] * Y_New + M[2, 0])
    res = data - Temp

    #
    ind_med = np.argwhere(abs(mask) > 0.5)
    img_3d_med = np.median(res[ind_med[:, 0], ind_med[:, 1]])
    res = np.asarray(res - (img_3d_med - 32767), np.uint16)
    res[ind[:, 0], ind[:, 1]] = 0

    return res
