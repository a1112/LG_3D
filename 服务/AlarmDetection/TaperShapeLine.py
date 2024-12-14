import numpy as np

from property.Base import CoilLineData, DataIntegration
from property.Data3D import LineData
from tools.data3dTool import getLengthData, getLengthDataByRotate


def find_max_min_value(line, noneDataValue, offset=0):
    """
    找到线段的最大最小值
    """
    line_copy = np.copy(line)
    line_copy[line_copy < noneDataValue] = 0
    mx, mn = int(np.argmax(line_copy)), int(np.argmin(line_copy))
    return [mx + offset, float(line_copy[mx])], [mn + offset, float(line_copy[mn])]


def findTaperShapeValue(line, noneDataValue, offset=0):
    l_line_index = int(len(line) / 2)
    max_minValue_l = find_max_min_value(line[:l_line_index], noneDataValue, offset)
    max_minValue_r = find_max_min_value(line[l_line_index:], noneDataValue, offset + l_line_index)
    return max_minValue_l, max_minValue_r


def findLRValue(line, offset=0):
    l_value = 0
    r_value = len(line) - 1
    for i in range(len(line)):
        if line[i] > 0:
            l_value = i
            break
    for i in range(len(line) - 1, -1, -1):
        if line[i] > 0:
            r_value = i
            break
    return l_value + offset, r_value + offset


def split_line(detLine, maskLine, noneDataValue, ceter_x, ceter_y):
    c1 = CoilLineData()
    c2 = CoilLineData()
    l_line_p = findLRValue(maskLine[:ceter_x])
    r_line_p = findLRValue(maskLine[ceter_x:], ceter_x)
    l_mm_v = findTaperShapeValue(detLine[l_line_p[0]:l_line_p[1]], noneDataValue)
    r_mm_v = findTaperShapeValue(detLine[r_line_p[0]:r_line_p[1]], noneDataValue, r_line_p[0])

    c1.lineData = detLine
    c2.lineData = detLine
    c1.centre = [ceter_x, ceter_y]
    c1.centre = [ceter_x, ceter_y]
    c1.linePoint = [l_line_p[0], l_line_p[1]]
    c2.linePoint = [r_line_p[0], r_line_p[1]]
    c1.rotation_angle = 180
    c2.rotation_angle = 0

    return l_mm_v, r_mm_v, [c1, c2]


def detection_taper_shape_by_rotation_angle(data_integration: DataIntegration, rotation_angle):
    """
    获取中心点 x,y ,根据角都计算.
    只适计算射线
    """
    p_center = data_integration.flatRollData.get_center()
    npy_data = data_integration.npyData
    mask = data_integration.npy_mask

    line_data = getLengthDataByRotate(npy_data, mask, p_center, rotation_angle, ray=True)
    line_data: LineData
    line_data.setDataIntegration(data_integration)
    line_data.detTaperShape()
    line_data.setRotationAngle(rotation_angle)
    return line_data
