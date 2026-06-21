from CoilDataBase.models import AlarmInfo

from AlarmDetection.Grading.alarm_flat_roll import grading_alarm_flat_roll
from AlarmDetection.Grading.alarm_loose_coil import grading_alarm_loose_coil
from AlarmDetection.Grading.alarm_taper_shape import grading_alarm_taper_shape
from AlarmDetection.Result.GradResult import AlarmGradResult

from Base.property.Base import CoilLineData, DataIntegration, DataIntegrationList
from Base.utils.Log import logger


GRADING_RECOVERABLE_ERRORS = (
    AttributeError,
    TypeError,
    ValueError,
    IndexError,
    OverflowError,
    ZeroDivisionError,
)


def _safe_grading(data_integration: DataIntegration, label: str, grading_func):
    try:
        return grading_func(data_integration)
    except GRADING_RECOVERABLE_ERRORS as e:
        coil_id = getattr(data_integration, "coilId", "")
        surface = getattr(data_integration, "key", getattr(data_integration, "surface", ""))
        error_msg = f"{label}检测失败: {e}"
        logger.warning(f"{coil_id} {surface} {error_msg}")
        return AlarmGradResult(3, error_msg, "")


def grading(data_integration: DataIntegration):
    """
        数据库提交判断级别
    Args:
        data_integration:
    Returns:

    """
    # 获取去向


    flat_roll_grad_info = _safe_grading(data_integration, "扁卷", grading_alarm_flat_roll)
    taper_shape_grad_info = _safe_grading(data_integration, "塔形", grading_alarm_taper_shape)
    alarm_loose_coil_info = _safe_grading(data_integration, "松卷", grading_alarm_loose_coil)


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
