from typing import List

from CoilDataBase.models import AlarmFlatRoll
from CoilDataBase.models import AlarmTaperShape
from CoilDataBase.models import AlarmInfo
from CONFIG import alarmConfigProperty, infoConfigProperty
from AlarmDetection.Configs.AlarmConfigProperty import AlarmGradResult
from AlarmDetection.Configs.LooseCoilConfig import LooseCoilConfig
from AlarmDetection.Configs.TaperShapeConfig import TaperShapeConfig
from AlarmDetection.Configs.FlatRollConfig import FlatRollConfig
from property.Base import CoilLineData, DataIntegration, DataIntegrationList
from property.Data3D import LineData
from property.detection3D import FlatRollData
from AlarmDetection.Configs.CoilInfo import CoilInfo


def gradingAlarmFlatRoll(alarm_flat_roll: AlarmFlatRoll, alarm_flat_roll_config: FlatRollConfig):
    """
    判断松卷的直接逻辑
    Args:
        alarm_flat_roll:
        alarm_flat_roll_config:
    Returns:
    """
    name, config_max, config_min, config_msg = alarm_flat_roll_config.get_config()
    error_msg = "正常"
    grad = 1
    if alarm_flat_roll.inner_circle_width <= config_min:
        error_msg = f"{name} 内径 {alarm_flat_roll.inner_circle_width} <= {config_min}"
        grad = 3
    elif alarm_flat_roll.inner_circle_width >= config_max:
        error_msg = f"{name} 内径 {alarm_flat_roll.inner_circle_width} >= {config_max}"
        grad = 3
    return AlarmGradResult(grad, error_msg, config_msg)


def gradingAlarmTaperShape(alarm_taper_shape_list: List[AlarmTaperShape], taper_shape_config: TaperShapeConfig):
    name, height_limit_list, inner, out, info = taper_shape_config.get_config()
    error_msg = "正常"
    grad = 1
    for alarmTaperShape in alarm_taper_shape_list:
        rotation_angle = alarmTaperShape.rotation_angle
        for height_limit_index, height_limit in enumerate(height_limit_list[::-1]):
            grading_level = 3 - height_limit_index
            if grad >= grading_level:
                continue
            if alarmTaperShape.out_taper_max_value >= height_limit:
                error_msg += f"外径最高值 {alarmTaperShape.out_taper_max_value} >= {height_limit} 检测角度{rotation_angle} \n"
                grad = grading_level
            if abs(alarmTaperShape.out_taper_min_value) >= height_limit:
                error_msg += f"外径最低值 abs({alarmTaperShape.out_taper_max_value}) >= {height_limit} 检测角度{rotation_angle} \n"
                grad = grading_level
            if alarmTaperShape.in_taper_max_value >= height_limit:
                error_msg += f"内径最高值 {alarmTaperShape.in_taper_max_value} >= {height_limit} 检测角度{rotation_angle} \n"
                grad = grading_level
            if alarmTaperShape.in_taper_min_value >= height_limit:
                error_msg += f"内径最低值 abs({alarmTaperShape.in_taper_min_value}) >= {height_limit} 检测角度{rotation_angle} \n"
                grad = grading_level
    return AlarmGradResult(grad, error_msg, taper_shape_config)


def gradingAlarmLooseCoil(detection_line_data: List[CoilLineData], loose_coil_config: LooseCoilConfig):
    name, width, info = loose_coil_config.get_config()
    grad_msg = ""
    grad = 1

    for lineData in detection_line_data:
        if lineData.max_width_mm > width:
            grad_msg += f"松卷检测最宽 {lineData.max_width_mm} 超过限制值 {width}"
            grad = 3
    return AlarmGradResult(grad, grad_msg, loose_coil_config)


def grading_alarm_flat_roll(data_integration: DataIntegration):
    next_code = data_integration.next_code
    alarm_flat_roll_config = alarmConfigProperty.get_alarm_flat_roll_config(next_code)  # 判及 参数
    flat_roll_data = data_integration.flatRollData
    inner_circle_width = data_integration.x_to_mm(flat_roll_data.inner_circle_width)
    flat_roll_data: FlatRollData
    alarmFlatRollConfig: FlatRollConfig
    name, config_max, config_min, config_msg = alarm_flat_roll_config.get_config()
    error_msg = "正常"
    grad = 1
    if inner_circle_width <= config_min:
        error_msg = f"{name} 内径 {inner_circle_width} <= {config_min}"
        grad = 3
    elif inner_circle_width >= config_max:
        error_msg = f"{name} 内径 {inner_circle_width} >= {config_max}"
        grad = 3
    return AlarmGradResult(grad, error_msg, config_msg)


def grading_alarm_taper_shape(data_integration: DataIntegration):
    next_code = data_integration.next_code
    taper_shape_config = alarmConfigProperty.get_taper_shape_config(next_code)  # 判及 参数
    name, height_limit_list, inner, out, info = taper_shape_config.get_config()
    error_msg = "正常"
    grad = 1

    max_outer_line_data = None
    max_inner_line_data = None
    for line_data in data_integration.lineDataDict.values():
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
        # if abs(out_taper_min_value) >= height_limit:
        #     error_msg += f"外径最低值 abs({out_taper_max_value}) >= {height_limit} 检测角度{rotation_angle} \n"
        #     grad = grading_level
        if in_taper_max_value >= height_limit:
            error_msg += f"内塔最高值 {in_taper_max_value} >= {height_limit} 检测角度{max_inner_line_data.rotation_angle} \n"
            grad = grading_level
        # if in_taper_min_value >= height_limit:
        #     error_msg += f"内径最低值 abs({in_taper_min_value}) >= {height_limit} 检测角度{rotation_angle} \n"
        #     grad = grading_level

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


def grading_alarm_loose_coil(data_integration: DataIntegration):
    next_code = data_integration.next_code
    loose_coil_config = alarmConfigProperty.get_loose_coil_config(next_code)  # 判及 参数
    name, width, info = loose_coil_config.get_config()
    grad_msg = ""
    grad = 1
    for lineData in data_integration.lineDataDict.values():
        max_zero_width_mm = lineData.max_zero_width_mm
        if max_zero_width_mm > width:
            grad_msg += f"松卷检测最宽 {max_zero_width_mm} 超过限制值 {width}"
            print(grad_msg)
            grad = 3
    return AlarmGradResult(grad, grad_msg, loose_coil_config)


def grading(data_integration: DataIntegration):
    """
        数据库提交判断级别
    Args:
        data_integration:
    Returns:

    """
    # 获取去向
    try:
        next_code = str(chr(int(data_integration.currentSecondaryCoil.Weight)))
    except:
        next_code = "N"
    next_name = infoConfigProperty.get_next(next_code)

    flat_roll_grad_info = grading_alarm_flat_roll(data_integration)
    taper_shape_grad_info = grading_alarm_taper_shape(data_integration)
    alarm_loose_coil_info = grading_alarm_loose_coil(data_integration)

    alarm_info = AlarmInfo(
        secondaryCoilId=data_integration.coilId,
        surface=data_integration.key,
        nextCode=next_code,
        nextName=next_name,
        taperShapeGrad=taper_shape_grad_info.grad,
        taperShapeMsg=taper_shape_grad_info.errorMsg,
        looseCoilGrad=alarm_loose_coil_info.grad,
        looseCoilMsg=alarm_loose_coil_info.errorMsg,
        flatRollGrad=flat_roll_grad_info.grad,
        flatRollMsg=flat_roll_grad_info.errorMsg,
        defectGrad=1,
        defectMsg="",
        grad=max(taper_shape_grad_info.grad, alarm_loose_coil_info.grad, flat_roll_grad_info.grad)
    )
    from CoilDataBase.Coil import add_obj
    add_obj(alarm_info)


def grading_all(data_integration_list: DataIntegrationList):
    """
    级别判断系统

    """
    for dataIntegration in data_integration_list:
        grading(dataIntegration)
