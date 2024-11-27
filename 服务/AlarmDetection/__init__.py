from typing import List

from CoilDataBase import Alarm
from property.Base import DataIntegration

from .AlarmFlatRoll import _detectionAlarmFlatRoll_, _detectionAlarmFlatRollAll_
from .CoilGrading import grading, gradingAll
from .TaperShape import _detectionTaperShape_, addAlarmTaperShape, _detectionTaperShapeAll_
from .AlarmLooseCoil import _detectionAlarmLooseCoil_, _detectionAlarmLooseCoilAll_


def detection(dataIntegration:DataIntegration):
    """
      检测的入口 old
    Args:
        dataIntegration:
        data:
    Returns:
    """

    #  提交松卷数据
    _detectionAlarmFlatRoll_(dataIntegration)   # 扁卷检测
    _detectionTaperShape_(dataIntegration)      # 塔形检测
    _detectionAlarmLooseCoil_(dataIntegration)  # 松卷检测
    grading(dataIntegration)

    Alarm.addAlarmFlatRoll(
        dataIntegration.alarmFlat_Roll
    )
    for alarmTaperShape in dataIntegration.alarmTaperShapeList:
        addAlarmTaperShape(dataIntegration,alarmTaperShape)



def detectionAll(dataIntegrationList:List[DataIntegration]):
    _detectionAlarmFlatRollAll_(dataIntegrationList)  # 扁卷检测
    _detectionTaperShapeAll_(dataIntegrationList)  # 塔形检测
    _detectionAlarmLooseCoilAll_(dataIntegrationList)  # 松卷检测
    gradingAll(dataIntegrationList)

    for dataIntegration in dataIntegrationList:
        if dataIntegration.hasDetectionError():
            continue
        Alarm.addAlarmFlatRoll(
            dataIntegration.alarmFlat_Roll
        )
        for alarmTaperShape in dataIntegration.alarmTaperShapeList:
            addAlarmTaperShape(dataIntegration, alarmTaperShape)