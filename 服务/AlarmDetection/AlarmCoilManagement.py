from CoilDataBase import Coil,Alarm
from CoilDataBase.models import AlarmFlatRoll


def getCoilAlarm(coil_id:str):
    FlatRollInfo={}
    AlarmFlatRollList = Alarm.getAlarmFlatRoll(coil_id)
    for alarmItem in AlarmFlatRollList[::-1]:
        alarmItem:AlarmFlatRoll
        FlatRollInfo[alarmItem.surface] = Coil.to_dict(alarmItem)


    TaperShapeInfo={
        "S":[],
        "L":[]

    }

    alarmTaperShapeList = Alarm.getAlarmTaperShape(coil_id)
    for alarmItem in alarmTaperShapeList:
        TaperShapeInfo[alarmItem.surface].append(Coil.to_dict(alarmItem))

    LooseCoil={
        "L":[],
        "S":[]
    }
    alarmLoose= Alarm.getAlarmLooseCoil(coil_id)
    for alarmItem in alarmLoose:
        LooseCoil[alarmItem.surface].append(Coil.to_dict(alarmItem))
    return {
        "FlatRoll":FlatRollInfo,
        "TaperShape":TaperShapeInfo,
        "LooseCoil":LooseCoil
    }