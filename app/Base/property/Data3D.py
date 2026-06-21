"""
封装3D数据拼接
"""
import json

import numpy as np
from skimage.draw import line

from Base.property.Types import Point3D
from Base.tools.alg import IQR_outliers
from Base.tools.tool import get_intersection_points

from CoilDataBase.models import LineData as LineDataModel
from CoilDataBase.models import PointData as PointDataModel


MIN_TAPER_SIDE_VALID_POINTS = 2


def valid_line_height_mask(line_, none_data_value=10):
    try:
        line_array = np.asarray(line_, dtype=float)
    except (TypeError, ValueError, OverflowError):
        return np.zeros(0, dtype=bool)
    if line_array.ndim != 2 or line_array.shape[1] < 3:
        row_count = line_array.shape[0] if line_array.ndim > 0 else 0
        return np.zeros(row_count, dtype=bool)
    return np.all(np.isfinite(line_array[:, :3]), axis=1) & (line_array[:, 2] > none_data_value)


def json_safe_line_points(line_):
    line_array = np.asarray(line_, dtype=float)
    line_array = np.where(np.isfinite(line_array), line_array, 0.0)
    return line_array.tolist()


def finite_model_number(value, field_name: str) -> float:
    try:
        value = float(value)
    except (TypeError, ValueError, OverflowError) as e:
        raise ValueError(f"塔形检测失败: {field_name}无效") from e
    if not np.isfinite(value):
        raise ValueError(f"塔形检测失败: {field_name}非有限")
    return value


def _positive_scale(value):
    try:
        value = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if not np.isfinite(value) or value <= 0:
        return None
    return value


def _point_coordinate(point, attr: str, index: int) -> float:
    value = getattr(point, attr, None)
    if value is None:
        try:
            value = point[index]
        except (TypeError, IndexError, KeyError, AttributeError) as e:
            raise ValueError("塔形检测失败: 中心点缺少坐标") from e
    try:
        value = float(value)
    except (TypeError, ValueError, OverflowError) as e:
        raise ValueError("塔形检测失败: 中心点坐标无效") from e
    if not np.isfinite(value):
        raise ValueError("塔形检测失败: 中心点坐标非有限")
    return value


def point_xy(point) -> tuple[float, float]:
    if point is None:
        raise ValueError("塔形检测失败: 中心点为空")
    return _point_coordinate(point, "x", 0), _point_coordinate(point, "y", 1)


def _outlier_cluster_size(values: np.ndarray, index: int, outlier_values: set[float]) -> int:
    if values[index] not in outlier_values:
        return 0

    count = 1
    left = index - 1
    while left >= 0 and values[left] in outlier_values:
        count += 1
        left -= 1
    right = index + 1
    while right < len(values) and values[right] in outlier_values:
        count += 1
        right += 1
    return count


def _is_isolated_iqr_outlier(values: np.ndarray, index: int, outlier_values: set[float]) -> bool:
    return _outlier_cluster_size(values, index, outlier_values) == 1


def find_line_max_min(line_, none_data_value, use_iqr=True, type_=None):
    """
    找到线段的最大最小值
    """
    if type_ is not None:
        type_ = "_" + type_
    else:
        type_ = ""
    line_ = line_[valid_line_height_mask(line_, none_data_value)]
    if line_.size == 0:
        return None, None

    values = line_[:, 2].astype(float)
    n = min(100, len(values))
    max_indices = np.argsort(values)[-n:][::-1]
    min_indices = np.argsort(values)[:n]

    max_index = int(max_indices[0])
    min_index = int(min_indices[0])
    if use_iqr:
        iqr_max_outliers = set(IQR_outliers(values[max_indices]).tolist())
        iqr_min_outliers = set(IQR_outliers(values[min_indices]).tolist())
        for i in max_indices:
            if _is_isolated_iqr_outlier(values, int(i), iqr_max_outliers):
                continue
            max_index = int(i)
            break
        for i in min_indices:
            if _is_isolated_iqr_outlier(values, int(i), iqr_min_outliers):
                continue
            min_index = int(i)
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
        base_mm = dataIntegration.median_3d_mm
        x = finite_model_number(self.x, "点X坐标")
        y = finite_model_number(self.y, "点Y坐标")
        z = finite_model_number(self.z, "点高度")
        z_mm = finite_model_number(dataIntegration.z_to_mm(z) - base_mm, "点毫米高度")
        return PointDataModel(
            secondaryCoilId=dataIntegration.secondary_coil_id,
            surface=dataIntegration.key,
            type=self.type_,
            x=x,
            y=y,
            z=z,
            z_mm=z_mm
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
        self._points_ = None
        self.npy_data = npy_data
        self.mask_image = mask_image
        self.p1 = p1
        self.p2 = p2
        self.image_threshold = 100

    @property
    def points(self):
        if self._points_ is None:
            self._points_ = self.all_image_line_points()
        return self._points_

    @property
    def ray_data(self):
        if self._ray_data_ is None:
            self._ray_data_ = self.all_image_line_points(mask=True, ray=True)
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
            non_zero_indices = np.where(valid_line_height_mask(arr, 10))[0]
            if non_zero_indices.size == 0:
                raise ValueError("塔形检测失败: 线数据为空或全零")
            # 起始索引和结束索引
            start_index = non_zero_indices[0]
            end_index = non_zero_indices[-1]
            self._ray_line_ = arr[start_index:end_index + 1]
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
        ray_line = self.ray_line
        p_start = ray_line[0]
        p_end = ray_line[-1]
        dx = float(p_start[0] - p_end[0])
        dy = float(p_start[1] - p_end[1])
        scale_x = _positive_scale(getattr(self.dataIntegration, "scan3dCoordinateScaleX", None))
        scale_y = _positive_scale(getattr(self.dataIntegration, "scan3dCoordinateScaleY", None))
        if scale_x is not None and scale_y is not None:
            return float(np.hypot(dx * scale_x, dy * scale_y))
        return self.dataIntegration.x_to_mm(self.length)

    @property
    def unit_distance_mm(self):
        return self.length_mm / max(self.count - 1, 1)

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
            direction_x = float(self.p2[0] - self.p1[0])
            direction_y = float(self.p2[1] - self.p1[1])
            ray_points = [
                [r, c] for r, c in zip(rr, cc)
                if (r - self.p1.x) * direction_x + (c - self.p1.y) * direction_y > 0
            ]
            if not ray_points:
                return np.empty((0, 3), dtype=np.int32)
            ray_points.sort(key=lambda point: (point[0] - self.p1.x) ** 2 + (point[1] - self.p1.y) ** 2)
            rr, cc = list(zip(*ray_points))
        if not mask:
            zz = self.npy_data[cc, rr]
            return np.array(list(zip(rr, cc, zz)))
        else:
            zz_mask = self.mask_image[cc, rr]
            zz = np.where(zz_mask > self.image_threshold, self.npy_data[cc, rr], 0)
            return np.array(list(zip(rr, cc, zz)))

    def mask_image_line_points(self, ray=True):
        """
        过滤mask外的点
        Returns:
        """
        return self.all_image_line_points(mask=True, ray=ray)

    def split_image_line_points(self, ray=True):
        """
        过滤mask外的点,然后进行分段
        Returns:
        """
        old_has_steel = False  # 记录上一个点的状态
        lines = []
        line_item = []
        for point in self.mask_image_line_points(ray=ray):
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
        if len(line_item) > 100:
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
        non_zero_indices = np.where(valid_line_height_mask(arr, 10))[0]
        if non_zero_indices.size == 0:
            raise ValueError("塔形检测失败: 线数据为空或全零")
        # 起始索引和结束索引
        start_index = non_zero_indices[0]
        end_index = non_zero_indices[-1]
        if end_index - start_index < 2:
            raise ValueError("塔形检测失败: 有效线数据过短")
        center_index = (start_index + end_index + 1) // 2
        inner_points = arr[start_index:center_index]
        outer_points = arr[center_index:end_index + 1]
        inner_valid_count = int(np.count_nonzero(valid_line_height_mask(inner_points, 10)))
        outer_valid_count = int(np.count_nonzero(valid_line_height_mask(outer_points, 10)))
        if min(inner_valid_count, outer_valid_count) < MIN_TAPER_SIDE_VALID_POINTS:
            raise ValueError(
                f"塔形检测失败: 塔形线有效点不足 inner={inner_valid_count} "
                f"outer={outer_valid_count} min={MIN_TAPER_SIDE_VALID_POINTS}"
            )
        # 最值检测
        self.inner_max_point, self.inner_min_point = find_line_max_min(inner_points, 10, self.useIQR, type_="inner")
        self.outer_max_point, self.outer_min_point = find_line_max_min(outer_points, 10, self.useIQR, type_="outer")
        if None in (self.inner_max_point, self.inner_min_point, self.outer_max_point, self.outer_min_point):
            raise ValueError("塔形检测失败: 内外圈有效线数据不足")

    def all_point_data_model(self, data_integration):
        return [self.inner_min_point.pointDataModel(data_integration),
                self.inner_max_point.pointDataModel(data_integration),
                self.outer_min_point.pointDataModel(data_integration),
                self.outer_max_point.pointDataModel(data_integration)
                ]

    def line_data_model(self, data_integration):
        base_mm = data_integration.median_3d_mm
        def rel_mm(z_value: float) -> float:
            return finite_model_number(
                data_integration.z_to_mm(z_value) - base_mm,
                "线数据毫米高度",
            )
        center_x, center_y = point_xy(data_integration.alarmData.flatRollData.get_center())
        return LineDataModel(
            secondaryCoilId=data_integration.secondary_coil_id,
            surface=data_integration.key,
            type="TaperShape",
            center_x=center_x,
            center_y=center_y,
            width=data_integration.width,
            height=data_integration.height,
            rotation_angle=self.rotation_angle,
            x1=self.p1.x,
            y1=self.p1.y,
            x2=self.p2.x,
            y2=self.p2.y,
            data=json.dumps(json_safe_line_points(self.ray_line), allow_nan=False),
            inner_min_value=self.inner_min_point.z,
            inner_min_value_mm=rel_mm(self.inner_min_point.z),
            inner_max_value=self.inner_max_point.z,
            inner_max_value_mm=rel_mm(self.inner_max_point.z),
            outer_min_value=self.outer_min_point.z,
            outer_min_value_mm=rel_mm(self.outer_min_point.z),
            outer_max_value=self.outer_max_point.z,
            outer_max_value_mm=rel_mm(self.outer_max_point.z)
        )


class Data3D:
    def __init__(self, data):
        self.data = data
