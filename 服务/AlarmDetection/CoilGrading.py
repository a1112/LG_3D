from typing import List

from CoilDataBase.models import AlarmFlatRoll
from CoilDataBase.models import AlarmTaperShape
from CoilDataBase.models import AlarmInfo
from CoilDataBase.Coil import addObj
from Globs import alarmConfigProperty, infoConfigProperty
from property.AlarmConfigProperty import AlarmFlatRollConfig, AlarmGradResult, TaperShapeConfig, LooseCoilConfig
from property.Base import CoilLineData, DataIntegration, DataIntegrationList


def gradingAlarmFlatRoll(alarm_flat_roll:AlarmFlatRoll, alarm_flat_roll_config:AlarmFlatRollConfig):
    """
    判断松卷的直接逻辑
    Args:
        alarm_flat_roll:
        alarm_flat_roll_config:
    Returns:
    """
    name,configMax, configMin, configMsg=alarm_flat_roll_config.getConfig()
    errorMsg="正常"
    grad=1
    if alarm_flat_roll.inner_circle_width<=configMin:
        errorMsg=f"{name} 内径 {alarm_flat_roll.inner_circle_width} <= {configMin}"
        grad=3
    elif alarm_flat_roll.inner_circle_width>=configMax:
        errorMsg=f"{name} 内径 {alarm_flat_roll.inner_circle_width} >= {configMax}"
        grad=3
    return AlarmGradResult(grad, errorMsg,configMsg)

def gradingAlarmTaperShape(alarm_taper_shape_list:List[AlarmTaperShape], taper_shape_config:TaperShapeConfig):
    name,height_limit_list,inner,out,info = taper_shape_config.getConfig()
    error_msg="正常"
    grad=1
    for alarmTaperShape in alarm_taper_shape_list:
        rotation_angle = alarmTaperShape.rotation_angle
        for height_limit_index,height_limit in enumerate(height_limit_list[::-1]):
            grading_level=3-height_limit_index
            if grad>=grading_level:
                continue
            if alarmTaperShape.out_taper_max_value>=height_limit:
                error_msg+=f"外径最高值 {alarmTaperShape.out_taper_max_value} >= {height_limit} 检测角度{rotation_angle} \n"
                grad=grading_level
            if abs(alarmTaperShape.out_taper_min_value)>=height_limit:
                error_msg+=f"外径最低值 abs({alarmTaperShape.out_taper_max_value}) >= {height_limit} 检测角度{rotation_angle} \n"
                grad=grading_level
            if alarmTaperShape.in_taper_max_value>=height_limit:
                error_msg+=f"内径最高值 {alarmTaperShape.in_taper_max_value} >= {height_limit} 检测角度{rotation_angle} \n"
                grad=grading_level
            if alarmTaperShape.in_taper_min_value>=height_limit:
                error_msg+=f"内径最低值 abs({alarmTaperShape.in_taper_min_value}) >= {height_limit} 检测角度{rotation_angle} \n"
                grad=grading_level
    return AlarmGradResult(grad, error_msg, taper_shape_config)

def gradingAlarmLooseCoil(detection_line_data:List[CoilLineData], loose_coil_config:LooseCoilConfig):
    name,width,info = loose_coil_config.getConfig()
    grad_msg=""
    grad=1

    for lineData in detection_line_data:
        if lineData.max_width_mm>width:
            grad_msg+=f"松卷检测最宽 {lineData.max_width_mm} 超过限制值 {width}"
            grad=3
    return AlarmGradResult(grad, grad_msg, loose_coil_config)

def grading(data_integration:DataIntegration):

    """
        数据库提交判断级别
    Args:
        data_integration:

    Returns:

    """
    # 获取去向
    next_code =str(chr(int(data_integration.currentSecondaryCoil.Weight)))
    next_name = infoConfigProperty.getNext(next_code)
    flat_roll_grad_info = gradingAlarmFlatRoll(data_integration.alarmFlat_Roll,alarmConfigProperty.getAlarmFlatRollConfig(next_code))
    taper_shape_grad_info = gradingAlarmTaperShape(data_integration.alarmTaperShapeList, alarmConfigProperty.getTaperShapeConfig(next_code))
    alarm_loose_coil_info = gradingAlarmLooseCoil(data_integration.detectionLineData, alarmConfigProperty.getLooseCoilConfig(next_code))

    alarm_info = AlarmInfo(
        secondaryCoilId=data_integration.coilId,
        surface=data_integration.key,
        nextCode=next_code,
        nextName = next_name,
        taperShapeGrad=taper_shape_grad_info.grad,
        taperShapeMsg=taper_shape_grad_info.errorMsg,
        looseCoilGrad=alarm_loose_coil_info.grad,
        looseCoilMsg=alarm_loose_coil_info.errorMsg,
        flatRollGrad=flat_roll_grad_info.grad,
        flatRollMsg=flat_roll_grad_info.errorMsg,
        defectGrad=1,
        defectMsg="",
        grad=max(taper_shape_grad_info.grad,alarm_loose_coil_info.grad,flat_roll_grad_info.grad)
    )
    addObj(alarm_info)


def gradingAll(data_integration_list:DataIntegrationList):
    for dataIntegration in data_integration_list:
        grading(dataIntegration)