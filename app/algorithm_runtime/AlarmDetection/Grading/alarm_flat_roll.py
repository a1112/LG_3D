import math

from AlarmDetection.Result.GradResult import AlarmGradResult
from AlarmDetection.property import alarmConfigProperty
from Base.property.Base import DataIntegration
from AlarmDetection.Result.errors import record_alarm_error


def grading_alarm_flat_roll(data_integration: DataIntegration) -> AlarmGradResult:
    alarm_flat_roll_config = alarmConfigProperty.get_alarm_flat_roll_config(data_integration)  # 判及 参数
    flat_roll_data = data_integration.alarmData.flatRollData
    if flat_roll_data is None:
        detail = getattr(data_integration.alarmData, "flat_roll_error", "")
        record_alarm_error(data_integration, "flat_roll", detail or "无有效内外圈数据")
        return AlarmGradResult(3, f"扁卷检测失败: {detail or '无有效内外圈数据'}", alarm_flat_roll_config)
    inner_circle_width = flat_roll_data.inner_diameter_mm()
    name, config_max, config_min, config_msg = alarm_flat_roll_config.get_config().get_config()
    inner_circle_width = float(inner_circle_width)
    config_max, config_min = float(config_max), float(config_min)
    if not all(math.isfinite(value) for value in (inner_circle_width, config_max, config_min)):
        raise ValueError("扁卷内径或阈值非有限")
    if inner_circle_width <= 0 or config_min <= 0 or config_max <= config_min:
        raise ValueError("扁卷内径或阈值范围无效")
    error_msg = "正常"
    grad = 1
    if inner_circle_width <= config_min:
        error_msg = f"{name} 内径 {inner_circle_width} <= {config_min}"
        grad = 3
    elif inner_circle_width >= config_max:
        error_msg = f"{name} 内径 {inner_circle_width} >= {config_max}"
        grad = 3
    return AlarmGradResult(grad, error_msg, config_msg)

