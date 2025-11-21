from CoilDataBase.models import AlarmInfo

from AlarmDetection.Grading.alarm_flat_roll import grading_alarm_flat_roll
from AlarmDetection.Grading.alarm_loose_coil import grading_alarm_loose_coil
from AlarmDetection.Grading.alarm_taper_shape import grading_alarm_taper_shape

from Base.property.Base import CoilLineData, DataIntegration, DataIntegrationList


def grading(data_integration: DataIntegration):
    """
        数据库提交判断级别
    Args:
        data_integration:
    Returns:

    """
    # 获取去向


    flat_roll_grad_info = grading_alarm_flat_roll(data_integration)
    taper_shape_grad_info = grading_alarm_taper_shape(data_integration)
    alarm_loose_coil_info = grading_alarm_loose_coil(data_integration)


    alarm_info = AlarmInfo(
        secondaryCoilId=data_integration.coilId,
        surface=data_integration.key,
        nextCode=data_integration.next_code,
        nextName=data_integration.next_name,
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