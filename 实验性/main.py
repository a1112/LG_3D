import math
import os
import time

import cv2
import numpy as np

from untils import *

S = True  # 设置是否使用S类型数据
if S is True:
    # 路径配置：使用S类型数据
    data_path_U = "test_data/S_U"
    data_path_M = "test_data/S_M"
    data_path_D = "test_data/S_D"
else:
    # 路径配置：使用L类型数据
    data_path_U = "test_data/L_U"
    data_path_M = "test_data/L_M"
    data_path_D = "test_data/L_D"

seq_no = 32484  # 设置序列号

# 拼接不同路径的数据文件
data_path_U_2d = os.path.join(os.path.join(data_path_U, str(seq_no)), "2d/*.bmp")
data_path_U_3d = os.path.join(os.path.join(data_path_U, str(seq_no)), "3d/*.npy")

data_path_M_2d = os.path.join(os.path.join(data_path_M, str(seq_no)), "2d/*.bmp")
data_path_M_3d = os.path.join(os.path.join(data_path_M, str(seq_no)), "3d/*.npy")

data_path_D_2d = os.path.join(os.path.join(data_path_D, str(seq_no)), "2d/*.bmp")
data_path_D_3d = os.path.join(os.path.join(data_path_D, str(seq_no)), "3d/*.npy")

if __name__ == "__main__":
    a = time.time()
    # 合并2D数据
    part_2d_U = merge_2d(data_path_U_2d)
    part_2d_M = merge_2d(data_path_M_2d)
    part_2d_D = merge_2d(data_path_D_2d)

    # 合并3D数据
    part_3d_U = merge_3d(data_path_U_3d)
    part_3d_M = merge_3d(data_path_M_3d)
    part_3d_D = merge_3d(data_path_D_3d)

    # 预处理2D视角数据
    part_2d_U = preprocess(part_2d_U, S)
    part_2d_M = preprocess(part_2d_M, S)
    part_2d_D = preprocess(part_2d_D, S)

    # 预处理3D视角数据
    part_3d_U = preprocess(part_3d_U, S)
    part_3d_M = preprocess(part_3d_M, S)
    part_3d_D = preprocess(part_3d_D, S)

    # 计算2D数据组合
    rept12, rept23 = count_combin(part_2d_U, part_2d_M, part_2d_D)

    # 处理3D数据平面转换
    part_3d_U_flat, ZZ_sub_U = convert_to_flat_image_ing(part_3d_U)
    part_3d_M_flat, ZZ_sub_M = convert_to_flat_image_ing(part_3d_M)
    part_3d_D_flat, ZZ_sub_D = convert_to_flat_image_ing(part_3d_D)

    # 合并不同的3D数据结果
    res_3D = combin_image(part_3d_U_flat, part_3d_M_flat, part_3d_D_flat, rept12, rept23)
    res_3D_z = combin_image(ZZ_sub_U, ZZ_sub_M, ZZ_sub_D, rept12, rept23)
    res_3D_s = combin_image(part_3d_U, part_3d_M, part_3d_D, rept12, rept23)

    # 合并2D数据结果
    res_2D = combin_image(part_2d_U, part_2d_M, part_2d_D, rept12, rept23)

    # 获取ROI区域
    x, y, w, h = get_roi(res_2D)

    # 裁剪结果区域
    res_3D = res_3D[y:y + h, x:x + w]
    res_2D = res_2D[y:y + h, x:x + w]
    res_3D_z = res_3D_z[y:y + h, x:x + w]
    res_3D_s = res_3D_s[y:y + h, x:x + w]

    # 计算最小尺寸并调整图片大小
    size = min(w, h)
    img_3d = cv2.resize(res_3D, (size, size))
    img_2d = cv2.resize(res_2D, (size, size))
    img_3d_z = cv2.resize(res_3D_z, (size, size))
    img_3d_s = cv2.resize(res_3D_s, (size, size))

    # 保存3D图片
    cv2.imwrite("img_3d.jpg", img_3d)

    # 定义视野半径
    in_r = int(750 * 0.5 / 0.35)
    cx, cy = size // 2, size // 2
    print(in_r, size // 2)

    # 创建空白掩码图像
    mask = np.zeros(img_3d_z.shape, np.uint8)
    ind = np.argwhere(img_3d_z > 10)
    mask[ind[:, 0], ind[:, 1]] = 255

    # 对不同半径进行循环处理
    for r in range(in_r, size // 2, 50):
        mask = np.zeros((size, size), np.uint8)
        cv2.circle(mask, (cx, cy), r, 1, -1)
        cv2.circle(mask, (cx, cy), r - 100, 0, -1)

        img_2d_color = cv2.cvtColor(img_2d, cv2.COLOR_GRAY2BGR)
        cv2.circle(img_2d_color, (cx, cy), r, (0, 0, 255), 2)
        cv2.circle(img_2d_color, (cx, cy), r - 100, (0, 0, 255), 2)

        # 计算ROI区域
        m_roi = (img_3d_z * mask)
        ind = np.argwhere(m_roi > 10)

        # 按角度分组并计算z值的最大值
        ss = [[] for _ in range(73)]
        for i in range(0, ind.shape[0]):
            x = ind[i][1] - size / 2
            y = ind[i][0] - size / 2
            angle = math.atan2(y, x) * 180 / np.pi
            ind_temp = int((angle - (-180)) / 5)
            z = img_3d_z[ind[i][0], ind[i][1]]
            ss[ind_temp].append(z)

        # 获取每个角度范围内的最大z值
        max_temp = [np.max(np.array(s)) if len(s) > 0 else 0 for s in ss]
        print(max_temp)

    # 计算运行时间
    print(time.time() - a)

    # 显示结果
    cv2.namedWindow("res_3D", 0)
    cv2.imshow("res_3D", res_3D)
    cv2.namedWindow("res_2D", 0)
    cv2.imshow("res_2D", res_2D)
    cv2.waitKey(0)