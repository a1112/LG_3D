import json
from dataclasses import dataclass

import numpy as np
from CoilDataBase.Coil import add_obj
from CoilDataBase.models import AlarmTaperShape

from AlarmDetection.Result.GradResult import AlarmGradResult
from AlarmDetection.property import alarmConfigProperty
from Base.property.Base import DataIntegration
from Base.property.Data3D import LineData, find_line_max_min


@dataclass
class TaperLineMetrics:
    line_data: LineData
    inner_max_point: object
    inner_min_point: object
    outer_max_point: object
    outer_min_point: object
    ignored_inner_mm: float
    ignored_outer_mm: float
    used_point_count: int


def _rel_mm(data_integration: DataIntegration, z_value: float) -> float:
    return float(data_integration.z_to_mm(z_value) - data_integration.median_3d_mm)


def _height_limits(values) -> list[float]:
    if values is None:
        return []
    if not isinstance(values, (list, tuple)):
        values = [values]
    limits = []
    for value in values:
        try:
            limits.append(float(value))
        except (TypeError, ValueError):
            continue
    return sorted(limits)


def _non_negative_float(value) -> float:
    try:
        return max(0.0, float(value))
    except (TypeError, ValueError):
        return 0.0


def _coil_thickness_mm(data_integration: DataIntegration) -> float:
    secondary_coil = getattr(data_integration, "currentSecondaryCoil", None)
    return _non_negative_float(getattr(secondary_coil, "Thickness", 0))


def _positive_scale(value):
    try:
        scale = float(value)
    except (TypeError, ValueError):
        return None
    if scale <= 0:
        return None
    return scale


def _line_unit_distance_mm(data_integration: DataIntegration, line_points: np.ndarray) -> float:
    if len(line_points) < 2:
        return 0.0
    start = line_points[0]
    end = line_points[-1]
    dx = float(end[0] - start[0])
    dy = float(end[1] - start[1])
    scale_x = _positive_scale(getattr(data_integration, "scan3dCoordinateScaleX", None))
    scale_y = _positive_scale(getattr(data_integration, "scan3dCoordinateScaleY", None))
    if scale_x is not None and scale_y is not None:
        distance_mm = float(np.hypot(dx * scale_x, dy * scale_y))
    else:
        pixel_distance = float(np.hypot(dx, dy))
        if pixel_distance <= 0:
            return 0.0
        distance_mm = float(data_integration.x_to_mm(pixel_distance))
    if distance_mm <= 0:
        return 0.0
    return distance_mm / max(len(line_points) - 1, 1)


def _trim_line_segments(data_integration: DataIntegration,
                        line_data: LineData,
                        inner_ignore_count,
                        outer_ignore_count):
    try:
        line_points = np.asarray(line_data.ray_line)
    except AttributeError:
        return None, 0.0, 0.0, False
    except ValueError:
        return None, 0.0, 0.0, True

    if line_points.size == 0:
        return None, 0.0, 0.0, True
    line_points = line_points[np.isfinite(line_points[:, 2]) & (line_points[:, 2] > 10)]
    if len(line_points) < 4:
        return None, 0.0, 0.0, True

    thickness_mm = _coil_thickness_mm(data_integration)
    ignored_inner_mm = _non_negative_float(inner_ignore_count) * thickness_mm
    ignored_outer_mm = _non_negative_float(outer_ignore_count) * thickness_mm
    unit_distance_mm = _line_unit_distance_mm(data_integration, line_points)

    inner_skip = int(np.ceil(ignored_inner_mm / unit_distance_mm)) if unit_distance_mm > 0 else 0
    outer_skip = int(np.ceil(ignored_outer_mm / unit_distance_mm)) if unit_distance_mm > 0 else 0

    center_index = len(line_points) // 2
    inner_points = line_points[:center_index]
    outer_points = line_points[center_index:]
    if inner_skip > 0:
        inner_points = inner_points[inner_skip:]
    if outer_skip > 0:
        outer_points = outer_points[:-outer_skip]
    if len(inner_points) == 0 or len(outer_points) == 0:
        return None, ignored_inner_mm, ignored_outer_mm, True
    return (inner_points, outer_points), ignored_inner_mm, ignored_outer_mm, True


def _metrics_from_line(data_integration: DataIntegration,
                       line_data: LineData,
                       inner_ignore_count,
                       outer_ignore_count):
    line_segments, ignored_inner_mm, ignored_outer_mm, has_line_points = _trim_line_segments(
        data_integration,
        line_data,
        inner_ignore_count,
        outer_ignore_count
    )
    if line_segments is None:
        if has_line_points:
            return None
        required_attrs = ("outer_max_point", "outer_min_point", "inner_max_point", "inner_min_point")
        if not all(getattr(line_data, attr, None) is not None for attr in required_attrs):
            return None
        return TaperLineMetrics(
            line_data=line_data,
            inner_max_point=line_data.inner_max_point,
            inner_min_point=line_data.inner_min_point,
            outer_max_point=line_data.outer_max_point,
            outer_min_point=line_data.outer_min_point,
            ignored_inner_mm=ignored_inner_mm,
            ignored_outer_mm=ignored_outer_mm,
            used_point_count=0
        )

    inner_points, outer_points = line_segments
    inner_max_point, inner_min_point = find_line_max_min(inner_points, 10, True, type_="inner")
    outer_max_point, outer_min_point = find_line_max_min(outer_points, 10, True, type_="outer")
    if None in (inner_max_point, inner_min_point, outer_max_point, outer_min_point):
        return None
    return TaperLineMetrics(
        line_data=line_data,
        inner_max_point=inner_max_point,
        inner_min_point=inner_min_point,
        outer_max_point=outer_max_point,
        outer_min_point=outer_min_point,
        ignored_inner_mm=ignored_inner_mm,
        ignored_outer_mm=ignored_outer_mm,
        used_point_count=len(inner_points) + len(outer_points)
    )


def _valid_line_metrics(data_integration: DataIntegration,
                        inner_ignore_count,
                        outer_ignore_count) -> list[TaperLineMetrics]:
    line_data_dict = getattr(data_integration.alarmData, "lineDataDict", None) or {}
    valid_metrics = []
    required_attrs = ("outer_max_point", "outer_min_point", "inner_max_point", "inner_min_point")
    for line_data in line_data_dict.values():
        if not all(getattr(line_data, attr, None) is not None for attr in required_attrs):
            continue
        metrics = _metrics_from_line(data_integration, line_data, inner_ignore_count, outer_ignore_count)
        if metrics is not None:
            valid_metrics.append(metrics)
    return valid_metrics


def _select_max_metrics(data_integration: DataIntegration,
                        valid_metrics: list[TaperLineMetrics],
                        point_attr: str) -> TaperLineMetrics:
    return max(valid_metrics, key=lambda metrics: _rel_mm(data_integration, getattr(metrics, point_attr).z))


def _select_min_metrics(data_integration: DataIntegration,
                        valid_metrics: list[TaperLineMetrics],
                        point_attr: str) -> TaperLineMetrics:
    return min(valid_metrics, key=lambda metrics: _rel_mm(data_integration, getattr(metrics, point_attr).z))


def _grade_by_limits(value: float, height_limits: list[float]) -> int:
    grad = 1
    for index, height_limit in enumerate(reversed(height_limits)):
        grading_level = max(2, 3 - index)
        if value >= height_limit:
            grad = max(grad, grading_level)
            break
    return grad


def _matched_limit(value: float, height_limits: list[float]) -> float | None:
    for height_limit in reversed(height_limits):
        if value >= height_limit:
            return height_limit
    return None


def grading_alarm_taper_shape(data_integration: DataIntegration):
    taper_shape_config = alarmConfigProperty.get_taper_shape_config(data_integration)
    name, height_limit_list, inner, outer, info = taper_shape_config.get_config().get_config()
    height_limits = _height_limits(height_limit_list)

    valid_metrics = _valid_line_metrics(data_integration, inner, outer)
    if not valid_metrics:
        error_msg = "塔形检测失败: 无有效线数据"
        return AlarmGradResult(3, error_msg, taper_shape_config)

    max_outer_metrics = _select_max_metrics(data_integration, valid_metrics, "outer_max_point")
    min_outer_metrics = _select_min_metrics(data_integration, valid_metrics, "outer_min_point")
    max_inner_metrics = _select_max_metrics(data_integration, valid_metrics, "inner_max_point")
    min_inner_metrics = _select_min_metrics(data_integration, valid_metrics, "inner_min_point")

    out_taper_max_value = _rel_mm(data_integration, max_outer_metrics.outer_max_point.z)
    out_taper_min_value = _rel_mm(data_integration, min_outer_metrics.outer_min_point.z)
    in_taper_max_value = _rel_mm(data_integration, max_inner_metrics.inner_max_point.z)
    in_taper_min_value = _rel_mm(data_integration, min_inner_metrics.inner_min_point.z)

    deviations = [
        ("外塔最高值", out_taper_max_value, max_outer_metrics),
        ("外塔最低值", out_taper_min_value, min_outer_metrics),
        ("内塔最高值", in_taper_max_value, max_inner_metrics),
        ("内塔最低值", in_taper_min_value, min_inner_metrics),
    ]
    worst_label, worst_value, worst_metrics = max(deviations, key=lambda item: abs(item[1]))
    selected_metrics = [max_outer_metrics, min_outer_metrics, max_inner_metrics, min_inner_metrics]

    grad = _grade_by_limits(abs(worst_value), height_limits)

    messages = []
    if grad > 1:
        for label, value, metrics in deviations:
            matched_limit = _matched_limit(abs(value), height_limits)
            if matched_limit is None:
                continue
            if value >= 0:
                messages.append(
                    f"{label}{value:.2f} >= {matched_limit:.2f} "
                    f"检测角度{metrics.line_data.rotation_angle}"
                )
            else:
                messages.append(
                    f"{label}{value:.2f} <= -{matched_limit:.2f} "
                    f"检测角度{metrics.line_data.rotation_angle}"
                )
    error_msg = "\n".join(messages) if messages else "正常"

    add_obj(AlarmTaperShape(
        secondaryCoilId=data_integration.coilId,
        surface=data_integration.surface,
        out_taper_max_x=max_outer_metrics.outer_max_point.x,
        out_taper_max_y=max_outer_metrics.outer_max_point.y,
        out_taper_max_value=out_taper_max_value,
        out_taper_min_x=min_outer_metrics.outer_min_point.x,
        out_taper_min_y=min_outer_metrics.outer_min_point.y,
        out_taper_min_value=out_taper_min_value,
        in_taper_max_x=max_inner_metrics.inner_max_point.x,
        in_taper_max_y=max_inner_metrics.inner_max_point.y,
        in_taper_max_value=in_taper_max_value,
        in_taper_min_x=min_inner_metrics.inner_min_point.x,
        in_taper_min_y=min_inner_metrics.inner_min_point.y,
        in_taper_min_value=in_taper_min_value,
        rotation_angle=worst_metrics.line_data.rotation_angle,
        level=grad,
        err_msg=error_msg,
        data=json.dumps({
            "config_name": name,
            "height_limits": height_limits,
            "inner_ignore": inner,
            "outer_ignore": outer,
            "ignored_inner_mm": max(metrics.ignored_inner_mm for metrics in selected_metrics),
            "ignored_outer_mm": max(metrics.ignored_outer_mm for metrics in selected_metrics),
            "config_info": info,
            "outer_angle": max_outer_metrics.line_data.rotation_angle,
            "inner_angle": max_inner_metrics.line_data.rotation_angle,
            "outer_max_angle": max_outer_metrics.line_data.rotation_angle,
            "inner_max_angle": max_inner_metrics.line_data.rotation_angle,
            "outer_min_angle": min_outer_metrics.line_data.rotation_angle,
            "inner_min_angle": min_inner_metrics.line_data.rotation_angle,
            "outer_max_mm": out_taper_max_value,
            "outer_min_mm": out_taper_min_value,
            "inner_max_mm": in_taper_max_value,
            "inner_min_mm": in_taper_min_value,
            "worst_label": worst_label,
            "worst_mm": worst_value,
            "worst_abs_mm": abs(worst_value),
            "valid_line_count": len(valid_metrics),
        }, ensure_ascii=False)
    ))
    return AlarmGradResult(grad, error_msg, taper_shape_config)
