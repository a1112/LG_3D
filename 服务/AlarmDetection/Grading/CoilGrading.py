from typing import List

from CoilDataBase.models import AlarmFlatRoll
from CoilDataBase.models import AlarmTaperShape
from CoilDataBase.models import AlarmInfo

from AlarmDetection.Grading.alarm_flat_roll import grading_alarm_flat_roll
from AlarmDetection.Grading.alarm_loose_coil import grading_alarm_loose_coil
from AlarmDetection.Grading.alarm_taper_shape import grading_alarm_taper_shape
from CONFIG import infoConfigProperty
from AlarmDetection.Configs.AlarmConfigProperty import AlarmGradResult
from AlarmDetection.Configs.LooseCoilConfig import LooseCoilConfig
from AlarmDetection.Configs.TaperShapeConfig import TaperShapeConfig
from AlarmDetection.Configs.FlatRollConfig import FlatRollConfig
from property.Base import CoilLineData, DataIntegration, DataIntegrationList


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


   def grading(data_integration: DataIntegration):
    """
        数据库提交判断级别
    Args:
        data_integration:
    Returns:

    """
    # 获取去向
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
        dataIntegration.alarmData.commit()