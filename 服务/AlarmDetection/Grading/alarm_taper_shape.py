from CoilDataBase.Coil import add_obj
from CoilDataBase.models import AlarmTaperShape

from AlarmDetection.Result.GradResult import AlarmGradResult
from AlarmDetection.property import alarmConfigProperty
from property.Base import DataIntegration
from property.Data3D import LineData


def grading_alarm_taper_shape(data_integration: DataIntegration):

    next_code = data_integration.next_code
    taper_shape_config = alarmConfigProperty.get_taper_shape_config(next_code)  # 判及 参数
    name, height_limit_list, inner, out, info = taper_shape_config.get_config().get_config()
    error_msg = "正常"
    grad = 1

    max_outer_line_data = None
    max_inner_line_data = None
    for line_data in data_integration.alarmData.lineDataDict.values():
        if 225>line_data.rotation_angle>45: # 只检测一半角度
            continue
        if max_outer_line_data is None or line_data.outer_max_point.z > max_outer_line_data.outer_max_point.z:
            max_outer_line_data = line_data
        if max_inner_line_data is None or line_data.inner_max_point.z > max_inner_line_data.inner_max_point.z:
            max_inner_line_data = line_data

    line_data: LineData
    for height_limit_index, height_limit in enumerate(height_limit_list[::-1]):
        grading_level = 3 - height_limit_index
        if grad >= grading_level:
            continue
        out_taper_max_value = data_integration.z_to_mm(max_outer_line_data.outer_max_point.z)
        out_taper_min_value = data_integration.z_to_mm(max_outer_line_data.outer_min_point.z)
        in_taper_max_value = data_integration.z_to_mm(max_inner_line_data.inner_max_point.z)
        in_taper_min_value = data_integration.z_to_mm(max_inner_line_data.inner_min_point.z)

        if out_taper_max_value >= height_limit:
            error_msg += f"外塔最高值 {out_taper_max_value} >= {height_limit} 检测角度{max_outer_line_data.rotation_angle} \n"
            grad = grading_level
        if in_taper_max_value >= height_limit:
            error_msg += f"内塔最高值 {in_taper_max_value} >= {height_limit} 检测角度{max_inner_line_data.rotation_angle} \n"
            grad = grading_level

    add_obj(AlarmTaperShape(
        secondaryCoilId=data_integration.coilId,
        surface=data_integration.surface,
        out_taper_max_x=max_outer_line_data.outer_max_point.x,
        out_taper_max_y=max_outer_line_data.outer_max_point.y,
        out_taper_max_value=data_integration.z_to_mm(max_outer_line_data.outer_max_point.z),
        out_taper_min_x=max_outer_line_data.outer_max_point.x,
        out_taper_min_y=max_outer_line_data.outer_max_point.y,
        out_taper_min_value=data_integration.z_to_mm(max_outer_line_data.outer_max_point.z),
        in_taper_max_x=max_inner_line_data.inner_max_point.x,
        in_taper_max_y=max_inner_line_data.inner_max_point.y,
        in_taper_max_value=data_integration.z_to_mm(max_inner_line_data.inner_max_point.z),
        in_taper_min_x=max_inner_line_data.inner_max_point.x,
        in_taper_min_y=max_inner_line_data.inner_max_point.y,
        in_taper_min_value=data_integration.z_to_mm(max_inner_line_data.inner_max_point.z),
        rotation_angle=max_outer_line_data.rotation_angle,
        level=grad,
        err_msg=error_msg
    ))
    return AlarmGradResult(grad, error_msg, taper_shape_config)
