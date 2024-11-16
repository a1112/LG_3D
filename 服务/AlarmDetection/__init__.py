from CoilDataBase import Alarm
from property.Base import DataIntegration

from .AlarmFlatRoll import _detectionAlarmFlatRoll_
from .CoilGrading import grading
from .TaperShape import _detectionTaperShape_ , addAlarmTaperShape
from .AlarmLooseCoil import _detectionAlarmLooseCoil_
def detection(dataIntegration:DataIntegration):
    """
      检测的入口
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
    levelDict = {}




    Alarm.addAlarmFlatRoll(
        dataIntegration.alarmFlat_Roll
    )
    for alarmTaperShape in dataIntegration.alarmTaperShapeList:
        addAlarmTaperShape(dataIntegration,alarmTaperShape)
