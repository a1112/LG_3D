from typing import Union

from property.Base import DataIntegration, DataIntegrationList
from utils.DetectionSpeedRecord import DetectionSpeedRecord

from .AlarmFlatRoll import _detectionAlarmFlatRoll_, _detectionAlarmFlatRollAll_
from .CoilGrading import grading, gradingAll
from .TaperShape import _detection_taper_shape_, addAlarmTaperShape, _detection_taper_shape_all_
from .AlarmLooseCoil import _detectionAlarmLooseCoil_, _detectionAlarmLooseCoilAll_

def detection(dataIntegration: DataIntegration):
    """
      检测的入口 old
    Args:
        dataIntegration:
    Returns:
    """
    #  提交松卷数据
    _detectionAlarmFlatRoll_(dataIntegration)  # 扁卷检测
    _detection_taper_shape_(dataIntegration)  # 塔形检测
    _detectionAlarmLooseCoil_(dataIntegration)  # 松卷检测
    grading(dataIntegration)

    # Alarm.addAlarmFlatRoll(
    #     dataIntegration.alarmFlat_Roll
    # )
    # for alarmTaperShape in dataIntegration.alarmTaperShapeList:
    #     addAlarmTaperShape(dataIntegration,alarmTaperShape)


@DetectionSpeedRecord.timing_decorator("判级时间")
def detection_all(data_integration_list: Union[DataIntegrationList, DataIntegration]):
    _detectionAlarmFlatRollAll_(data_integration_list)  # 扁卷检测
    _detection_taper_shape_all_(data_integration_list)  # 塔形检测
    _detectionAlarmLooseCoilAll_(data_integration_list)  # 松卷检测
    # gradingAll(dataIntegrationList)

    # for dataIntegration in dataIntegrationList:
    #
    #     for alarmTaperShape in dataIntegration.alarmTaperShapeList:
    #         addAlarmTaperShape(dataIntegration, alarmTaperShape)
