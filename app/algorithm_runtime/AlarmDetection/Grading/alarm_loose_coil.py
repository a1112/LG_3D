import json
import math

from AlarmDetection.Result.GradResult import AlarmGradResult
from AlarmDetection.property import alarmConfigProperty
from Base.property.Base import DataIntegration
from Base.utils.Log import logger
from CoilDataBase.Alarm import addAlarmLooseCoil
from CoilDataBase.models import AlarmLooseCoil
from AlarmDetection.Result.errors import record_alarm_error


def grading_alarm_loose_coil(data_integration: DataIntegration) -> AlarmGradResult:
    loose_coil_config = alarmConfigProperty.get_loose_coil_config(data_integration)
    name, width, info = loose_coil_config.get_config().get_config()
    width = float(width)
    if not math.isfinite(width) or width <= 0:
        raise ValueError("松卷间隙限制必须为正的有限毫米数值")
    alarm_data = data_integration.alarmData
    measurements = getattr(alarm_data, "loose_coil_measurements", None)
    if measurements is None:
        from AlarmDetection.DataProcessing.AlarmLooseCoil import _detectionAlarmLooseCoil_
        measurements = _detectionAlarmLooseCoil_(data_integration)
    errors = getattr(alarm_data, "loose_coil_errors", [])
    for error in errors:
        record_alarm_error(data_integration, "loose_coil", error)
    if not measurements:
        if getattr(alarm_data, "taper_shape_disabled", False):
            return AlarmGradResult(1, "松卷检测关闭: 径向检测已关闭", loose_coil_config)
        message = "松卷检测失败: 无有效径向线数据"
        if errors:
            message += "；" + "；".join(errors[:3])
        record_alarm_error(data_integration, "loose_coil", message)
        return AlarmGradResult(3, message, loose_coil_config)
    worst = max(measurements, key=lambda item: item["max_width_mm"])
    max_width = worst["max_width_mm"]
    grad = 3 if max_width > width else 1
    grad_msg = (f"{name} 松卷检测最宽 {max_width:.2f} mm 超过限制值 {width:g} mm，"
                f"检测角度 {worst['rotation_angle']:g}度") if grad > 1 else "正常"
    if errors:
        grad_msg += "；部分径向线无效: " + "；".join(errors[:3])
    detail = AlarmLooseCoil(
        secondaryCoilId=data_integration.coilId,
        surface=data_integration.surface,
        max_width=max_width,
        rotation_angle=worst["rotation_angle"],
        level=grad,
        err_msg=grad_msg,
        data=json.dumps({
            "max_width_unit": "mm", "max_width_mm": max_width,
            "width_limit_mm": width, "config_name": name,
            "config_info": info, "measurements": measurements,
            "errors": errors,
        }, ensure_ascii=False, allow_nan=False),
    )
    try:
        addAlarmLooseCoil(detail)
    except Exception as e:
        logger.warning("save loose coil detail failed coil=%s surface=%s: %s",
                       data_integration.coilId, data_integration.surface, e)
        grad_msg += f"；松卷明细保存失败: {e}"
        record_alarm_error(data_integration, "loose_coil_commit", e)
    return AlarmGradResult(grad, grad_msg, loose_coil_config)
