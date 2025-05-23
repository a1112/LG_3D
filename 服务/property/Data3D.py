"""
封装3D数据拼接
"""
import json

import numpy as np
from skimage.draw import line

from property.Types import Point3D
from tools.alg import IQR_outliers
from tools.tool import get_intersection_points

from CoilDataBase.models import LineData as LineDataModel
from CoilDataBase.models import PointData as PointDataModel


def find_line_max_min(line_, none_data_value, use_iqr=True, type_=None):
    """
    找到线段的最大最小值
    """
    if type_ is not None:
        type_ = "_" + type_
    else:
        type_ = ""
    line_ = line_[line_[:, 2] > none_data_value]
    values = line_[:, 2]
    n = 100  # 你可以选择n的值
    max_indices = np.argsort(values)[-n:][::-1]  # 排序并反转获取最大值的前n个索引
    # 获取前n个最小值的索引
    min_indices = np.argsort(values)[:n]  # 排序并获取最小值的前n个索引
    if not len(max_indices) or not len(min_indices):
        return None, None

    max_index = max_indices[0]
    min_index = min_indices[0]
    if use_iqr:
        iqr_max_outliers = IQR_outliers(values[max_indices])  # 异常值
        iqr_min_outliers = IQR_outliers(values[min_indices])  # 异常值
        for i in max_indices:
            if values[i] in iqr_max_outliers:
                continue
            max_index = i
            break
        for i in min_indices:
            if values[i] in iqr_min_outliers:
                continue
            min_index = i
            break
    return PointData(line_[max_index], "max" + type_), PointData(line_[min_index], "min" + type_)


class PointData(Point3D):
    """
    点数据
    """

    def __init__(self, point, type_="point"):
        self.type_ = type_
        super().__init__(point[0], point[1], point[2])

    def pointDataModel(self, dataIntegration):
        return PointDataModel(
            secondaryCoilId=dataIntegration.secondary_coil_id,
            surface=dataIntegration.key,
            type=self.type_,
            x=float(self.x),
            y=float(self.y),
            z=float(self.z),
            z_mm=float(dataIntegration.z_to_mm(self.z))
        )


class LineData:
    """
    p1 到 p2 的 深度,数据
    """

    def __init__(self, npy_data, mask_image, p1, p2):
        self._zero_mm_ = None
        self._ray_line_mm_ = None
        self._ray_line_ = None
        self._ray_data_ = None
        self.rotation_angle = None
        self.useIQR = True
        self.outer_max_point = None
        self.outer_min_point = None
        self.inner_min_point = None
        self.inner_max_point = None
        self.dataIntegration = None
        self._points_ = []
        self.npy_data = npy_data
        self.mask_image = mask_image
        self.p1 = p1
        self.p2 = p2
        self.image_threshold = 100

    @property
    def points(self):
        if not self._points_:
            self._points_ = self.all_image_line_points()
        return self._points_

    @property
    def ray_data(self):
        if self._ray_data_ is None:
            self._ray_data_ = self.all_image_line_points(mask=True, ray=True).astype(np.int32)
        return self._ray_data_

    @property
    def zero_mm(self):
        if self._zero_mm_ is None:
            self._zero_mm_ = self.dataIntegration.zero_mm()
        return self._zero_mm_

    def mmNoneData(self, mmValue):
        return mmValue < self.zero_mm + 10

    @property
    def ray_line(self):
        if self._ray_line_ is None:
            arr = self.ray_data
            non_zero_indices = np.where(arr[:, 2] != 0)[0]
            # 起始索引和结束索引
            start_index = non_zero_indices[0]
            end_index = non_zero_indices[-1]
            self._ray_line_ = arr[start_index:end_index]
        return self._ray_line_

    @property
    def ray_line_mm(self):
        if self._ray_line_mm_ is None:
            self._ray_line_mm_ = self.dataIntegration.point_to_mm(self.ray_line)
        return self._ray_line_mm_

    def get_edge_point(self):
        """
        获取与图像边缘相交的两个点
        """
        h, w = self.mask_image.shape
        return get_intersection_points(self.p1, self.p2, w, h)

    @property
    def count(self):
        return len(self.ray_line)

    @property
    def length(self):
        ray_line = self.ray_line
        p_start = ray_line[0]
        p_end = ray_line[-1]
        return np.sqrt((p_start[0] - p_end[0]) ** 2 + (p_start[1] - p_end[1]) ** 2)

    @property
    def length_mm(self):
        return self.dataIntegration.x_to_mm(self.length)

    @property
    def unit_distance_mm(self):
        return self.length_mm / self.count

    @property
    def none_data_sub(self):
        indices = np.where(self.ray_line_mm[:, 2] < self.zero_mm + 10)[0]
        segments = []
        unit_distance_mm = self.unit_distance_mm
        if len(indices) > 0:
            # Start with the first segment
            start = indices[0]
            length = 1

            for i in range(1, len(indices)):
                if indices[i] == indices[i - 1] + 1:
                    length += 1
                else:
                    segments.append((int(start), int(length), float(start * unit_distance_mm),
                                     float(length * unit_distance_mm)))  # End the current segment
                    start = indices[i]
                    length = 1
            segments.append(
                (int(start), int(length), float(start * unit_distance_mm), float(length * unit_distance_mm)))

        return segments

    @property
    def max_zero_width_mm(self):
        max_width = 0

        for item in self.none_data_sub:
            if item[-1] > max_width:
                max_width = item[-1]
        return max_width

    def point_has_data(self, point):
        return point > self.image_threshold

    def all_image_line_points(self, mask=True, ray=True):
        """
        获取 直线经过图像 的所有点 x，y ,z
        """
        p1, p2 = self.get_edge_point()
        rr, cc = line(p1.x, p1.y, p2.x, p2.y)
        if ray:  # 射线模式,只对线段进行判断
            def directionEqual(direction1, direction2):  # 计算两个方向是否相等
                return direction1[0] == direction2[0] and direction1[1] == direction2[1]

            direction = (self.p2[0] - self.p1[0] > 0, self.p2[1] - self.p1[1] > 0)
            rr, cc = list(zip(*[[r, c] for r, c in zip(rr, cc) if
                                directionEqual(direction, (r - self.p1.x > 0, c - self.p1.y > 0))]))
        if not mask:
            zz = self.npy_data[cc, rr]
            return np.array(list(zip(rr, cc, zz)))
        else:
            zz_mask = self.mask_image[cc, rr]
            zz = np.where(zz_mask > self.image_threshold, self.npy_data[cc, rr], 0)
            return np.array(list(zip(rr, cc, zz)))

    def mask_image_line_points(self):
        """
        过滤mask外的点
        Returns:
        """
        return self.all_image_line_points(mask=True)

    def split_image_line_points(self):
        """
        过滤mask外的点,然后进行分段
        Returns:
        """
        old_has_steel = False  # 记录上一个点的状态
        lines = []
        line_item = []
        for point in self.mask_image_line_points():
            """
            扫描一次实现全部的分段
            """
            has_steel = self.point_has_data(point[2])
            if has_steel and not old_has_steel:
                # 新的线段
                line_item.append(point)

            elif has_steel and old_has_steel:
                line_item.append(point)
            elif not has_steel and old_has_steel:
                if len(line_item) > 100:
                    lines.append(line_item)
                    line_item = []
            old_has_steel = has_steel
        if line_item:
            lines.append(line_item)
        return lines

    def set_data_integration(self, data_integration):
        self.dataIntegration = data_integration

    def set_rotation_angle(self, angle):
        self.rotation_angle = angle

    def det_taper_shape(self):
        """
        返回到 内外塔形的最大最小值
        Returns:
        """
        points = self.ray_data
        arr = points
        non_zero_indices = np.where(arr[:, 2] != 0)[0]
        # 起始索引和结束索引
        start_index = non_zero_indices[0]
        end_index = non_zero_indices[-1]
        center_index = (start_index + end_index) // 2
        inner_points = arr[start_index:center_index]
        outer_points = arr[center_index:end_index]
        # 最值检测
        self.inner_max_point, self.inner_min_point = find_line_max_min(inner_points, 10, self.useIQR, type_="inner")
        self.outer_max_point, self.outer_min_point = find_line_max_min(outer_points, 10, self.useIQR, type_="outer")

    def all_point_data_model(self, data_integration):
        return [self.inner_min_point.pointDataModel(data_integration),
                self.inner_max_point.pointDataModel(data_integration),
                self.outer_min_point.pointDataModel(data_integration),
                self.outer_max_point.pointDataModel(data_integration)
                ]

    def line_data_model(self, data_integration):
        return LineDataModel(
            secondaryCoilId=data_integration.secondary_coil_id,
            surface=data_integration.key,
            type="TaperShape",
            center_x=data_integration.alarmData.flatRollData.get_center().x,
            center_y=data_integration.alarmData.flatRollData.get_center().y,
            width=data_integration.width,
            height=data_integration.height,
            rotation_angle=self.rotation_angle,
            x1=self.p1.x,
            y1=self.p1.y,
            x2=self.p2.x,
            y2=self.p2.y,
            data=json.dumps(self.ray_line.tolist()),
            inner_min_value=self.inner_min_point.z,
            inner_min_value_mm=data_integration.z_to_mm(self.inner_min_point.z),
            inner_max_value=self.inner_max_point.z,
            inner_max_value_mm=data_integration.z_to_mm(self.inner_max_point.z),
            outer_min_value=self.outer_min_point.z,
            outer_min_value_mm=data_integration.z_to_mm(self.outer_min_point.z),
            outer_max_value=self.outer_max_point.z,
            outer_max_value_mm=data_integration.z_to_mm(self.outer_max_point.z)
        )


class Data3D:
    def __init__(self, data):
        self.data = data
