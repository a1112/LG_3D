from AlarmDetection.Result.GradResult import AlarmGradResult
from AlarmDetection.property import alarmConfigProperty
from property.Base import DataIntegration


def grading_alarm_loose_coil(data_integration: DataIntegration):
    next_code = data_integration.next_code
    loose_coil_config = alarmConfigProperty.get_loose_coil_config(next_code)  # 判及 参数
    name, width, info = loose_coil_config.get_config().get_config()
    grad_msg = ""
    grad = 1
    for lineData in data_integration.alarmData.lineDataDict.values():
        max_zero_width_mm = lineData.max_zero_width_mm
        if max_zero_width_mm > width:
            grad_msg += f"松卷检测最宽 {max_zero_width_mm} 超过限制值 {width}"
            print(grad_msg)
            grad = 3
    return AlarmGradResult(grad, grad_msg, loose_coil_config)
