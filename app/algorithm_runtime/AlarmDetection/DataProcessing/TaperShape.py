import math
from typing import Union

import cv2

import Globs
from Base.property.Base import DataIntegrationList
from Base.property.Types import Point2D, DetectionTaperShapeType
from CoilDataBase.models import AlarmTaperShape
from CoilDataBase import Alarm
from Base.tools.data3dTool import getP2ByRotate
from Base.utils.Log import logger
from utils.DetectionSpeedRecord import DetectionSpeedRecord
from AlarmDetection.DataProcessing.TaperShapeLine import *


def addAlarmTaperShape(dataIntegration: DataIntegration, alarmTaperShape: AlarmTaperShape):
    alarmTaperShape.secondaryCoilId = dataIntegration.coilId
    alarmTaperShape.surface = dataIntegration.key
    Alarm.addAlarmTaperShape(alarmTaperShape)


def detection_taper_shape_by_area(data_integration: DataIntegration):
    pass


@DetectionSpeedRecord.timing_decorator("_detectionTaperShape_")
def _detection_taper_shape_(data_integration: DataIntegration):
    print("塔形检测")

    # 角度检测
    line_data_dict = {}
    for rotate in [i * 20 for i in range(18)]:
        line_data_dict[int(rotate)] = detection_taper_shape_by_rotation_angle(data_integration, rotate)


    # inner_max_point_values = np.array([line.inner_max_point.z for line in lineDataList])
    # print((inner_max_point_values-dataIntegration.median_non_zero)*dataIntegration.scan3dCoordinateScaleZ)
    #
    # inner_max_point_values = np.array([line.inner_min_point.z for line in lineDataList])
    # print((inner_max_point_values-dataIntegration.median_non_zero)*dataIntegration.scan3dCoordinateScaleZ)
    #
    # inner_max_point_values = np.array([line.outer_max_point.z for line in lineDataList])
    # print((inner_max_point_values-dataIntegration.median_non_zero)*dataIntegration.scan3dCoordinateScaleZ)
    #
    # inner_max_point_values = np.array([line.outer_min_point.z for line in lineDataList])
    # print((inner_max_point_values-dataIntegration.median_non_zero)*dataIntegration.scan3dCoordinateScaleZ)

    # 提交全部深度检测点
    #
    return line_data_dict
    #
    # x_cet_mm,y_cet_mm,accuracy_x=(dataIntegration.flatRollData.inner_circle_center_x,
    #                    dataIntegration.alarmFlat_Roll.inner_circle_center_y,
    #                    dataIntegration.alarmFlat_Roll.accuracy_x)
    # cx, cy=int(x_cet_mm/accuracy_x),int(y_cet_mm/accuracy_x)
    # # maskNpy =
    # maskLine = dataIntegration.npy_mask[cy,]
    # detLine = dataIntegration.npyData[cy,]
    # median_3d_mm = dataIntegration.median_3d_mm
    # scan3dCoordinateScaleZ = dataIntegration.scan3dCoordinateScaleZ
    # noneDataValue = -(median_3d_mm-100)
    # detLine=detLine*scan3dCoordinateScaleZ-median_3d_mm
    # l_mm_v, r_mm_v, coilLineDataList = split_line(detLine,maskLine,noneDataValue,cx,cy)
    #
    #
    # def getAlarmTaperShape(mm_v,rotation_angle):
    #
    #     out_v,in_rv=mm_v
    #

    #
    # def init_mm_v(mm_v):
    #     l_v,r_v=mm_v
    #     l_v_max,lv_min=l_v
    #     r_v_max,rv_min=r_v
    #     l_v_max=l_v_max[0],0,l_v_max[1]
    #     lv_min=lv_min[0],0,lv_min[1]
    #     rv_max=r_v_max[0],0,r_v_max[1]
    #     rv_min=rv_min[0],0,rv_min[1]
    #     return [[l_v_max,lv_min],[rv_max,rv_min]]
    #
    # ats1 = getAlarmTaperShape(init_mm_v(l_mm_v),180)
    # ats2 = getAlarmTaperShape(init_mm_v(r_mm_v)[::-1], 0)
    #
    # dataIntegration.alarmTaperShapeList=[ats1,ats2]
    #
    # dataIntegration.detectionLineData = coilLineDataList


@DetectionSpeedRecord.timing_decorator("_detectionTaperShapeA_")
def _detectionTaperShapeA_(dataIntegration: DataIntegration):
    print("塔形检测A")
    lineDataDict = {}
    # p_center = dataIntegration.flatRollData.get_center()
    npyData = (dataIntegration.npy_data - dataIntegration.__median_non_zero__) * dataIntegration.scan3dCoordinateScaleZ
    img_2d = dataIntegration.npy_image
    mask = dataIntegration.npy_mask
    ind = np.argwhere(mask == 0)
    npyData[ind[:, 0], ind[:, 1]] = 0
    inner_taper, inner_ind_max_r, inner_ind_max_a, outer_taper, outer_ind_max_r, outer_ind_max_a, p_c = count_taper2(
        npyData,
        img_2d)

    logger.debug(f"{dataIntegration.coilId}  {dataIntegration.surface}")
    logger.debug(["内圈塔形:", inner_taper, "半径:", inner_ind_max_r, "角度:", inner_ind_max_a])
    logger.debug(["外圈塔形:", outer_taper, "半径:", outer_ind_max_r, "角度:", outer_ind_max_a])

    # p_center error :  中心点由 count_taper 返回
    p_inner = getP2ByRotate(p_c, np.pi / 180 * inner_ind_max_a, inner_ind_max_a)
    p_outer = getP2ByRotate(p_c, np.pi / 180 * inner_ind_max_a, inner_ind_max_a)
    Alarm.addObj(  # AlarmTaperShape 为旧版本对象，为 x 角度的检测塔形数值， 借用显示，新对象移动到 LineData 中
        # 目前无最低值，临时结构
        AlarmTaperShape(
            secondaryCoilId=dataIntegration.coilId,
            surface=dataIntegration.surface,
            out_taper_max_x=p_outer.x,
            out_taper_max_y=p_outer.y,
            out_taper_max_value=outer_taper,
            out_taper_min_x=p_outer.x,
            out_taper_min_y=p_outer.y,
            out_taper_min_value=outer_taper,
            in_taper_max_x=p_inner.x,
            in_taper_max_y=p_inner.y,
            in_taper_max_value=inner_taper,
            in_taper_min_x=p_inner.x,
            in_taper_min_y=p_inner.y,
            in_taper_min_value=inner_taper,
            rotation_angle=outer_ind_max_a,
            level=3 if outer_taper > 50 or inner_taper > 50 else 1
        )
    )
    # th_3d = 100
    # import cv2
    # def cloud_to_color_fast(depth, exp=1, mode=0):
    #     exp_f = 127 / exp
    #     depth_image = np.clip(depth, a_min=-1 * exp_f, a_max=exp_f)
    #
    #     if mode == 0:
    #         im_color = cv2.applyColorMap(cv2.convertScaleAbs(depth_image, alpha=exp, beta=127), cv2.COLORMAP_JET)
    #     elif mode == 1:
    #         im_color = cv2.applyColorMap(cv2.convertScaleAbs(depth_image, alpha=exp, beta=127), cv2.COLORMAP_SUMMER)
    #     else:
    #         im_color = cv2.applyColorMap(cv2.convertScaleAbs(depth_image, alpha=exp, beta=127), cv2.COLORMAP_JET)
    #     return im_color
    # Image_3D_Depth = np.asarray(npyData)
    # print("ss", np.max(npyData), np.min(npyData))
    # Image_3D_Depth = np.where(Image_3D_Depth < th_3d, Image_3D_Depth, th_3d)
    # Image_3D_Depth = np.where(Image_3D_Depth > -1 * th_3d, Image_3D_Depth, -1 * th_3d)
    # Image_2D_Depth = cloud_to_color_fast(Image_3D_Depth, 1, mode=0)
    # tools.tool.showImage(Image_2D_Depth)
    #
    return lineDataDict


def count_taper(data, img, angle_num=36, roll_num=100, in_r=750, fe=0.35):
    """
    data:转化为相对深度的数据
    roll_inv:表示计算圆环数据每次环区域厚度
    """
    in_r = int(((in_r - 200) * 0.5) / fe)
    h, w = data.shape[:2]
    size = min(w, h)
    img_3d = cv2.resize(data, (size, size))
    img_2d = cv2.resize(img, (size, size))

    # 矩阵扩充，主要为了保证最后的圆环能够框到边
    offset = 200
    size_exp = size + offset
    img_3d_exp = np.zeros((size_exp, size_exp), np.float32)
    img_3d_exp[offset // 2:-offset // 2, offset // 2:-offset // 2] = img_3d
    img_2d_exp = np.zeros((size_exp, size_exp), np.uint8)
    img_2d_exp[offset // 2:-offset // 2, offset // 2:-offset // 2] = img_2d

    # 以图像的中心为圆心来计算
    cx, cy = size_exp // 2, size_exp // 2
    data_alarm_all = []
    r_list = []
    angle_inv = 360 // angle_num

    for r in range(in_r, size_exp // 2, roll_num // 2):  # 步长小于厚度，用来保证有一定的重叠
        r_list.append(r)
        mask = np.zeros((size_exp, size_exp), np.uint8)
        # cv2.circle(mask, (cx, cy), r, 1, -1)
        # cv2.circle(mask, (cx, cy), r - roll_num, 0, -1)
        bShow = False
        if bShow is True:
            img_2d_exp_color = cv2.cvtColor(img_2d_exp, cv2.COLOR_GRAY2BGR)
            cv2.circle(img_2d_exp_color, (cx, cy), r, (0, 0, 255), 2)
            cv2.circle(img_2d_exp_color, (cx, cy), r - roll_num, (0, 0, 255), 2)
            cv2.namedWindow("img_2d_exp_color", 0)
            cv2.imshow("img_2d_exp_color", img_2d_exp_color)
            cv2.waitKey(0)

        img_3d_roll_roi = (img_3d_exp * mask)
        ind = np.argwhere(img_3d_roll_roi > 10)
        ind_v = np.argwhere(img_3d_roll_roi <= 10)
        mean = np.mean(img_3d_roll_roi[ind_v[:, 0], ind_v[:, 0]])

        data_deep = []
        for i in range(0, angle_num):
            data_deep.append([])

        # 对超出设定值的数据进行统计，这里由于设了阈值，所以会降低一定的计算量，设定的阈值越高，计算量越低
        for i in range(0, ind.shape[0]):
            x = ind[i][1] - size_exp / 2
            y = ind[i][0] - size_exp / 2
            angle = math.atan2(y, x) * 180 / np.pi
            ind_temp = min(int((angle - (-180)) / angle_inv), angle_num - 1)
            z = img_3d_exp[ind[i][0], ind[i][1]]
            # print(ind_temp)
            data_deep[ind_temp].append(z)

        # 上面已经将圆环分成不同角度的等份数据，接下来就是计算每份数据中的最大值（去噪后的）
        data_alarm = []
        for i in range(0, angle_num):
            if len(data_deep[i]) > 0:
                deep_num = 60
                deep_inv = 5
                num = []
                z_value = []
                for j in range(0, deep_num):
                    num.append(0)
                    z_value.append([])
                for j in range(0, len(data_deep[i])):
                    t_ind = int(min(data_deep[i][j] // deep_inv, deep_num - 1))
                    num[t_ind] += 1
                    z_value[t_ind].append(data_deep[i][j])
                num = np.array(num)
                t_ind = np.argwhere(num > 100)
                if t_ind.shape[0] > 0:
                    # print(t_ind[-1])
                    index = t_ind[-1][0]
                    data_alarm.append(round(np.max(np.array(z_value[index])), 2))
                else:
                    data_alarm.append(mean)
            else:
                data_alarm.append(mean)
        # print(data_alarm)
        data_alarm_all.append(data_alarm)
        # print(len(data_alarm), data_alarm)
    # 根据所有的报警
    data_alarm_all = np.array(data_alarm_all)
    r, a = data_alarm_all.shape[:2]
    data_alarm_all_inner = data_alarm_all[:r // 2, :]
    data_alarm_all_outer = data_alarm_all[r // 2:, :]
    inner_ind_max = np.argmax(data_alarm_all_inner)
    inner_ind_max_row, inner_ind_max_col = np.unravel_index(inner_ind_max, data_alarm_all_inner.shape)
    outer_ind_max = np.argmax(data_alarm_all_outer)
    outer_ind_max_row, outer_ind_max_col = np.unravel_index(outer_ind_max, data_alarm_all_outer.shape)
    inner_taper = data_alarm_all_inner[inner_ind_max_row, inner_ind_max_col]
    outer_taper = data_alarm_all_outer[outer_ind_max_row, outer_ind_max_col]
    inner_ind_max_r = r_list[inner_ind_max_row] * fe
    inner_ind_max_a = angle_inv * inner_ind_max_col
    outer_ind_max_r = r_list[outer_ind_max_row] * fe
    outer_ind_max_a = angle_inv * outer_ind_max_col

    # test
    data_alarm_all_inner1 = data_alarm_all[:r // 2, 9:18]
    data_alarm_all_outer1 = data_alarm_all[r // 2:, 9:18]
    inner_ind_max1 = np.argmax(data_alarm_all_inner1)
    inner_ind_max_row1, inner_ind_max_col1 = np.unravel_index(inner_ind_max1, data_alarm_all_inner1.shape)
    outer_ind_max1 = np.argmax(data_alarm_all_outer1)
    outer_ind_max_row1, outer_ind_max_col1 = np.unravel_index(outer_ind_max1, data_alarm_all_outer1.shape)
    inner_taper1 = data_alarm_all_inner1[inner_ind_max_row1, inner_ind_max_col1]
    outer_taper1 = data_alarm_all_outer1[outer_ind_max_row1, outer_ind_max_col1]
    inner_ind_max_r1 = r_list[inner_ind_max_row1] * fe
    inner_ind_max_a1 = angle_inv * (inner_ind_max_col1 + 9)
    outer_ind_max_r1 = r_list[outer_ind_max_row1] * fe
    outer_ind_max_a1 = angle_inv * (outer_ind_max_col1 + 9)
    # print("内圈塔形1:", inner_taper1, "半径1:", inner_ind_max_r1, "角度1:", inner_ind_max_a1)
    # print("外圈塔形1:", outer_taper1, "半径1:", outer_ind_max_r1, "角度1:", outer_ind_max_a1)

    # return inner_taper, inner_ind_max_r, inner_ind_max_a, outer_taper, outer_ind_max_r, outer_ind_max_a, Point2D(cx, cy)
    return inner_taper1, inner_ind_max_r1, inner_ind_max_a1, outer_taper1, outer_ind_max_r1, outer_ind_max_a1, Point2D(
        cx, cy)


def count_taper2(data, img, angle_num=36, roll_num=100, in_r=750, fe=0.35):
    """
    data: 转化为相对深度的数据
    img: 图像数据
    angle_num: 分成的角度数量
    roll_num: 每个圆环的厚度
    in_r: 内半径
    fe: 放大因子
    """
    # 计算实际内半径
    in_r = int(((in_r - 200) * 0.5) / fe)
    h, w = data.shape[:2]
    size = min(w, h)

    # 缩放图像到统一大小
    img_3d = cv2.resize(data, (size, size))
    img_2d = cv2.resize(img, (size, size))

    # 扩充矩阵，确保最后的圆环可以框到边缘
    offset = 200
    size_exp = size + offset
    img_3d_exp = np.zeros((size_exp, size_exp), np.float32)
    img_2d_exp = np.zeros((size_exp, size_exp), np.uint8)

    img_3d_exp[offset // 2:-offset // 2, offset // 2:-offset // 2] = img_3d
    img_2d_exp[offset // 2:-offset // 2, offset // 2:-offset // 2] = img_2d

    # 以图像的中心为圆心
    cx, cy = size_exp // 2, size_exp // 2
    angle_inv = 360 // angle_num

    # 初始化输出数据结构
    data_alarm_all = []
    r_list = []

    # 计算圆环的半径
    for r in range(in_r, size_exp // 2, roll_num // 2):
        r_list.append(r)
        mask = np.zeros((size_exp, size_exp), np.uint8)

        # 计算当前圆环范围内的数据
        img_3d_roll_roi = (img_3d_exp * mask)
        ind = np.argwhere(img_3d_roll_roi > 10)
        ind_v = np.argwhere(img_3d_roll_roi <= 10)
        mean = np.mean(img_3d_roll_roi[ind_v[:, 0], ind_v[:, 0]])

        data_deep = [[] for _ in range(angle_num)]

        # 对每个有效数据点进行处理
        for i in range(ind.shape[0]):
            x = ind[i][1] - size_exp / 2
            y = ind[i][0] - size_exp / 2
            angle = math.atan2(y, x) * 180 / np.pi
            ind_temp = min(int((angle - (-180)) / angle_inv), angle_num - 1)
            z = img_3d_exp[ind[i][0], ind[i][1]]
            data_deep[ind_temp].append(z)

        # 对每个角度分区的深度值进行统计
        data_alarm = []
        for i in range(angle_num):
            if data_deep[i]:
                deep_num = 60
                deep_inv = 5
                num = np.zeros(deep_num)
                z_value = [[] for _ in range(deep_num)]

                for z in data_deep[i]:
                    t_ind = int(min(z // deep_inv, deep_num - 1))
                    num[t_ind] += 1
                    z_value[t_ind].append(z)

                t_ind = np.argwhere(num > 100)
                if t_ind.shape[0] > 0:
                    index = t_ind[-1][0]
                    data_alarm.append(round(np.max(np.array(z_value[index])), 2))
                else:
                    data_alarm.append(mean)
            else:
                data_alarm.append(mean)

        data_alarm_all.append(data_alarm)

    # 根据所有的报警数据进行分析
    data_alarm_all = np.array(data_alarm_all)
    r, a = data_alarm_all.shape[:2]
    data_alarm_all_inner = data_alarm_all[:r // 2, :]
    data_alarm_all_outer = data_alarm_all[r // 2:, :]

    # 找到最大报警值对应的内外圈数据
    inner_ind_max = np.argmax(data_alarm_all_inner)
    inner_ind_max_row, inner_ind_max_col = np.unravel_index(inner_ind_max, data_alarm_all_inner.shape)
    outer_ind_max = np.argmax(data_alarm_all_outer)
    outer_ind_max_row, outer_ind_max_col = np.unravel_index(outer_ind_max, data_alarm_all_outer.shape)

    # 内外圈塔形信息
    inner_taper = data_alarm_all_inner[inner_ind_max_row, inner_ind_max_col]
    outer_taper = data_alarm_all_outer[outer_ind_max_row, outer_ind_max_col]

    # 计算半径和角度
    inner_ind_max_r = r_list[inner_ind_max_row] * fe
    inner_ind_max_a = angle_inv * inner_ind_max_col
    outer_ind_max_r = r_list[outer_ind_max_row] * fe
    outer_ind_max_a = angle_inv * outer_ind_max_col

    # 返回计算结果
    return inner_taper, inner_ind_max_r, inner_ind_max_a, outer_taper, outer_ind_max_r, outer_ind_max_a, Point2D(cx, cy)





def _detection_taper_shape_all_(data_integration_list: Union[DataIntegrationList, DataIntegration]):
    """
    no doc
    """
    print("塔形检测 all")
    for dataIntegration in data_integration_list:
        if DetectionTaperShapeType.WK_TYPE in Globs.control.taper_shape_type:
            _detectionTaperShapeA_(dataIntegration)
            dataIntegration.alarmData.set_line_data_dict({})
        if DetectionTaperShapeType.LINE_TYPE in Globs.control.taper_shape_type:
            dataIntegration.alarmData.set_line_data_dict( _detection_taper_shape_(dataIntegration))
        # dataIntegration.lineDataDict 应由 _detectionTaperShape_ 返回

