from CoilDataBase.models import AlarmInfo

from AlarmDetection.Grading.alarm_flat_roll import grading_alarm_flat_roll
from AlarmDetection.Grading.alarm_loose_coil import grading_alarm_loose_coil
from AlarmDetection.Grading.alarm_taper_shape import grading_alarm_taper_shape
from AlarmDetection.Grading.alarm_defects import grading_alarm_defects
from AlarmDetection.Result.GradResult import AlarmGradResult
from AlarmDetection.Result.errors import alarm_error_result, merge_alarm_errors, record_alarm_error

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
        record_alarm_error(data_integration, f"grading_{label}", e)
        return AlarmGradResult(3, error_msg, "")


def _data_integration_log_fields(data_integration: DataIntegration):
    coil_id = getattr(data_integration, "coilId", "")
    surface = getattr(data_integration, "key", getattr(data_integration, "surface", ""))
    return coil_id, surface


def grading(data_integration: DataIntegration):
    """
        数据库提交判断级别
    Args:
        data_integration:
    Returns:

    """
    # 获取去向


    flat_roll_grad_info = _safe_grading(data_integration, "扁卷", grading_alarm_flat_roll)
    alarm_data = getattr(data_integration, "alarmData", None)
    if alarm_data is not None:
        alarm_data.flat_roll_grad_result = flat_roll_grad_info
    taper_shape_grad_info = _safe_grading(data_integration, "塔形", grading_alarm_taper_shape)
    alarm_loose_coil_info = _safe_grading(data_integration, "松卷", grading_alarm_loose_coil)
    defect_grad_info = getattr(getattr(data_integration, "alarmData", None),
                               "defect_grad_result", None)
    if defect_grad_info is None:
        defect_grad_info = _safe_grading(data_integration, "缺陷", grading_alarm_defects)


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
        defectGrad=defect_grad_info.grad,
        defectMsg=defect_grad_info.errorMsg,
        grad=max(taper_shape_grad_info.grad, alarm_loose_coil_info.grad,
                 flat_roll_grad_info.grad, defect_grad_info.grad)
    )
    from CoilDataBase.Coil import add_obj
    try:
        add_obj(alarm_info)
    except Exception as e:
        coil_id, surface = _data_integration_log_fields(data_integration)
        logger.warning(f"{coil_id} {surface} 保存综合报警失败: {e}")
        record_alarm_error(data_integration, "alarm_info_commit", e)
    return alarm_error_result(data_integration)


def grading_all(data_integration_list: DataIntegrationList):
    """
    级别判断系统

    """
    errors = {}
    for dataIntegration in data_integration_list:
        coil_id, surface = _data_integration_log_fields(dataIntegration)
        try:
            merge_alarm_errors(errors, grading(dataIntegration))
        except Exception as e:
            logger.warning(f"{coil_id} {surface} 综合报警分级失败: {e}")
            record_alarm_error(dataIntegration, "grading", e)
        try:
            merge_alarm_errors(errors, dataIntegration.alarmData.commit())
        except Exception as e:
            logger.warning(f"{coil_id} {surface} 报警明细提交失败: {e}")
            record_alarm_error(dataIntegration, "alarm_detail_commit", e)
        merge_alarm_errors(errors, alarm_error_result(dataIntegration))
    return errors
