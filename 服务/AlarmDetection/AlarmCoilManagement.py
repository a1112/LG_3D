from CoilDataBase import Coil, Alarm, tool
from CoilDataBase.models import AlarmFlatRoll


def get_coil_alarm(coil_id: str):
    """
    获取报警数据 （分别查询）
    """
    flat_roll_info = {}
    alarm_flat_roll_list = Alarm.getAlarmFlatRoll(coil_id)
    for alarmItem in alarm_flat_roll_list[::-1]:
        alarmItem: AlarmFlatRoll
        flat_roll_info[alarmItem.surface] = tool.to_dict(alarmItem)

    taper_shape_info = {
        "S": [],
        "L": []

    }

    alarm_taper_shape_list = Alarm.getAlarmTaperShape(coil_id)
    for alarmItem in alarm_taper_shape_list:
        taper_shape_info[alarmItem.surface].append(tool.to_dict(alarmItem))

    LooseCoil = {
        "L": [],
        "S": []
    }
    alarm_loose = Alarm.getAlarmLooseCoil(coil_id)
    for alarmItem in alarm_loose:
        LooseCoil[alarmItem.surface].append(tool.to_dict(alarmItem))
    return {
        "FlatRoll": flat_roll_info,
        "TaperShape": taper_shape_info,
        "LooseCoil": LooseCoil
    }
