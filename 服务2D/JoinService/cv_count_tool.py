from queue import Queue
import statistics

import cv2
from collections import defaultdict
from threading import Thread
import numpy as np

from utils.MultiprocessColorLogger import logger

from configs.CONFIG import DEBUG


class ThreadImageShow(Thread):
    def __init__(self):
        super(ThreadImageShow, self).__init__()
        self.queue = Queue(maxsize=10)
        self.start()


    def add_show_image(self, image, name):
        self.queue.put([image,name])

    def run(self):
        while True:
            try:
                image, name = self.queue.get()
                cv2.namedWindow(name, cv2.WINDOW_NORMAL)
                cv2.resizeWindow(name,480,480)
                cv2.imshow(name,image)
                cv2.waitKey(0)

            except BaseException as e:
                print(e)
                cv2.destroyAllWindows()
                pass
threadImageShow = ThreadImageShow()

def im_show(image, title="Image"):
    # 显示结果
    threadImageShow.add_show_image(image, title)

def draw_points(gray_img, contour, intersections):
    # 创建彩色图像用于可视化
    output = cv2.cvtColor(gray_img, cv2.COLOR_GRAY2BGR)

    # 绘制最大轮廓（绿色）
    if contour is not None:
        cv2.drawContours(output, [contour], -1, (0, 255, 0), 2)

    # 绘制所有交点（红色）
    for pt in intersections:
        cv2.circle(output, pt, 3, (0, 0, 255), -1)

    # 添加说明文字
    cv2.putText(output, "Contour (Green)", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    cv2.putText(output, "Intersections (Red)", (10, 60),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    im_show(output, "Contour and Intersections")

def get_max_contour_and_intersections(gray_image):
    """
    获取灰度图像的最大轮廓及其与y=0到h的水平线交点

    参数:
        gray_image: 输入的灰度图像(二维numpy数组)

    返回:
        max_contour: 最大轮廓(numpy数组)
        intersections: 与y=0到h的水平线交点列表[(x1,y1), (x2,y2), ...]
    """
    # 存储交点
    intersections = []
    # 检查轮廓是否与每条水平线相交

    nonzero_indices = np.nonzero(gray_image)
    start_index_y = -1
    pre_p = None
    for index_y,index_x in zip(nonzero_indices[0], nonzero_indices[1]):
        if index_y>start_index_y:
            if pre_p is not None:
                intersections.append(pre_p)
            intersections.append([int(index_y), int(index_x)])
        pre_p = [int(index_y), int(index_x)]
        start_index_y = index_y
    return None, intersections

def get_max_contour_and_intersections_(gray_image):
    """
    获取灰度图像的最大轮廓及其与y=0到h的水平线交点

    参数:
        gray_image: 输入的灰度图像(二维numpy数组)

    返回:
        max_contour: 最大轮廓(numpy数组)
        intersections: 与y=0到h的水平线交点列表[(x1,y1), (x2,y2), ...]
    """

    # 二值化图像
    _, binary = cv2.threshold(gray_image, 100, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    # 查找轮廓
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # 如果没有找到轮廓，返回None
    if not contours:
        return None, []

    # 找到最大轮廓
    max_contour = max(contours, key=cv2.contourArea)

    # 获取图像高度
    h = gray_image.shape[0]

    # 存储交点
    intersections = []

    # 检查轮廓是否与每条水平线相交
    for y in range(h,2):
        # 创建一条水平线(从最左到最右)
        line_start = (0, y)
        line_end = (gray_image.shape[1], y)

        # 检查轮廓与水平线的交点
        for i in range(len(max_contour) - 1):
            pt1 = tuple(max_contour[i][0])
            pt2 = tuple(max_contour[i + 1][0])

            # 计算线段交点
            intersect = line_intersection((line_start, line_end), (pt1, pt2))
            if intersect:
                intersections.append(intersect)

    return max_contour, intersections


def line_intersection(line1, line2):
    """
    计算两条线段的交点
    """
    (x1, y1), (x2, y2) = line1
    (x3, y3), (x4, y4) = line2

    denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if denom == 0:  # 平行线
        return None

    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
    u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / denom

    if 0 <= t <= 1 and 0 <= u <= 1:  # 检查是否在线段内
        x = x1 + t * (x2 - x1)
        y = y1 + t * (y2 - y1)
        return (int(x), int(y))
    return None

def get_median_value(value_list):
    value_list=[v for v in value_list if v>50]
    if len(value_list) < 5:
        return 0
    return statistics.median(value_list)

def inbounds(point, shape):
    """
    检查点是否在图像边界内
    """
    h, w = shape
    return 3 <= point[0] < w-3 and 3 <= point[1] < h-3

def get_the_difference_int(ins):
    median_l, median_r = get_median_value(ins[0]), get_median_value(ins[1])
    if median_l == 0 and median_r == 0:
        return 0
    if median_l == 0:
        return median_r
    if median_r == 0:
        return median_l
    return max(median_l , median_l)
    # ins_all = ins[0] + ins[1]
    # return sum(ins_all)/len(ins_all) if len(ins_all) > 0 else 0


def get_the_difference(list1, list2, shape):
    h, w = shape
    difference_l_list = []
    difference_r_list = []
    for i in range(h):
        if i in list1 and i in list2:
            l_list = list1[i]
            r_list = list2[i]
            if len(l_list) == 0 or len(r_list) == 0:
                continue

            l1_l= l_list[0]
            r1_l = r_list[0]
            l1_r = l_list[-1]
            r1_r = r_list[-1]
            if inbounds((l1_l, i), shape) and inbounds((r1_l, i), shape):
                    difference_l_list.append(abs(l1_l - r1_l))
            if inbounds((l1_r, i), shape) and inbounds((r1_r, i), shape):
                    difference_r_list.append(abs(l1_r - r1_r))

    return difference_l_list, difference_r_list

def format_intersections(intersections, shape):
    """
    格式化交点列表为字符串
    """
    h, w = shape
    r_dict = defaultdict(list)
    for p in intersections:
        # if p[1] <= 1 or p[1] >= h-1 or p[0] <= 1 or p[0] >= w-1:
        #     continue
        if p[1] in r_dict[p[0]]:
            continue
        r_dict[p[0]].append(p[1])
    return r_dict


def format_intersections_list(intersections_list_):
    """
    格式化交点列表
    """
    intersections_list = [i for i in intersections_list_ if i > 100]
    ave_value = statistics.mean(intersections_list) if intersections_list else 0
    formatted = []
    for intersections in intersections_list_:
        if intersections > 100:
            formatted.append(intersections)
        else:
            formatted.append(ave_value)
    return formatted

def draw_debug_image(image,ins_int,d_count):
    """
    绘制
    """
    h,w,*_ = image.shape
    image = cv2.putText(image,fr"{ins_int}",(int(w/2)-20,int(h/2)),cv2.FONT_HERSHEY_SIMPLEX,1,(0,255,0),3)
    return image

def hconcat_list(image_list,ins_int_list):
    """
    水平拼接图像列表
    """
    if not image_list:
        return None
    add_image_list = [image_list[0].copy()]
    for index in range(len(ins_int_list)):
        try:
            h,w,*_= image_list[index+1].shape
            ins_int = ins_int_list[index]
            try:
                if ins_int == 0:
                    ins_int=ins_int_list[index-1]
            except IndexError:
                ins_int = ins_int_list[index+1]
            d_count = int(w - ins_int)
            item_image = image_list[index+1][:,d_count:]

            if DEBUG:
                item_image = draw_debug_image(item_image,ins_int,d_count)
            add_image_list.append(item_image)
        except IndexError:
            # raise
            logger.error(f"<hconcat_list IndexError>{index+1}")
    count_image = cv2.hconcat(add_image_list)
    return count_image

def get_intersections(mask_list):
    intersections = []
    for gray_index in range(len(mask_list)-1):
        _, intersections_l = get_max_contour_and_intersections(mask_list[gray_index])
        _, intersections_r = get_max_contour_and_intersections(mask_list[gray_index+1])

        format_intersections_l = format_intersections(intersections_l, mask_list[gray_index].shape)
        format_intersections_r = format_intersections(intersections_r, mask_list[gray_index+1].shape)



        ins = get_the_difference(format_intersections_l,format_intersections_r,mask_list[gray_index].shape)
        intersections.append(get_the_difference_int(ins))


        # print(fr"format_intersections_l {format_intersections_l}")
        # print(fr"format_intersections_r {format_intersections_r}")
        print(fr"get_the_difference {ins}")
        print(fr"get_the_difference_int(ins) {get_the_difference_int(ins)}")
    format_intersections_ = format_intersections_list(intersections)
    logger.debug(fr"intersections   {intersections}")
    print(fr"_intersections_   {intersections}")
    print(fr"format_intersections_   {format_intersections_}")
    return format_intersections_