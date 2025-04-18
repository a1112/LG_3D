from typing import Union

from property.Base import DataIntegration, DataIntegrationList
from utils.DetectionSpeedRecord import DetectionSpeedRecord


from .Grading.CoilGrading import grading, grading_all
from .DataProcessing.TaperShape import  _detection_taper_shape_all_
from .DataProcessing.AlarmLooseCoil import  _detectionAlarmLooseCoilAll_
from .DataProcessing.AlarmDefect import _detectionAlarmDefectAll_
from .DataProcessing.AlarmFlatRoll import  _detectionAlarmFlatRollAll_

@DetectionSpeedRecord.timing_decorator("判级时间")
def detection_all(data_integration_list: Union[DataIntegrationList, DataIntegration]):
    """
    判级
    """
    _detectionAlarmFlatRollAll_(data_integration_list)  # 扁卷检测
    _detection_taper_shape_all_(data_integration_list)  # 塔形检测
    _detectionAlarmLooseCoilAll_(data_integration_list) # 松卷检测
    _detectionAlarmDefectAll_(data_integration_list)    # 缺陷检测
    grading_all(data_integration_list)

    # for dataIntegration in dataIntegrationList:
    #
    #     for alarmTaperShape in dataIntegration.alarmTaperShapeList:
    #         addAlarmTaperShape(dataIntegration, alarmTaperShape)
