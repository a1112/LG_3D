from CoilDataBase.models import AlarmFlatRoll

from AlarmDetection.Result.GradResult import AlarmGradResult
from AlarmDetection.Configs.FlatRollConfig import FlatRollConfig
from AlarmDetection.Result.FlatRollData import FlatRollData
from AlarmDetection.property import alarmConfigProperty
from property.Base import DataIntegration


def grading_alarm_flat_roll(data_integration: DataIntegration):
    alarm_flat_roll_config = alarmConfigProperty.get_alarm_flat_roll_config(data_integration)  # 判及 参数
    flat_roll_data = data_integration.alarmData.flatRollData
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

