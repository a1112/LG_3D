from .DataProcessing.TaperShape import _detection_taper_shape_all_
from .DataProcessing.AlarmLooseCoil import _detectionAlarmLooseCoilAll_
from .DataProcessing.AlarmDefect import _detectionAlarmDefectAll_
from .DataProcessing.AlarmFlatRoll import _detectionAlarmFlatRollAll_

from utils.DetectionSpeedRecord import DetectionSpeedRecord

from .Grading.CoilGrading import grading, grading_all
from Base.utils.Log import logger


def _run_alarm_stage(label, stage, data_integration_list):
    try:
        stage(data_integration_list)
    except Exception as e:
        coil_ids = [
            getattr(data, "coilId", None) for data in data_integration_list
        ]
        logger.exception("alarm stage failed stage=%s coils=%s error=%s",
                         label, coil_ids, e)


@DetectionSpeedRecord.timing_decorator("判级时间")
def detection_all(
        data_integration_list):  #  Union[DataIntegrationList, DataIntegration]
    """
    判级
    """
    stages = (
        ("flat_roll", _detectionAlarmFlatRollAll_),
        ("taper_shape", _detection_taper_shape_all_),
        ("loose_coil", _detectionAlarmLooseCoilAll_),
        ("defect", _detectionAlarmDefectAll_),
        ("grading", grading_all),
    )
    for label, stage in stages:
        _run_alarm_stage(label, stage, data_integration_list)

    # for dataIntegration in dataIntegrationList:
    #
    #     for alarmTaperShape in dataIntegration.alarmTaperShapeList:
    #         addAlarmTaperShape(dataIntegration, alarmTaperShape)
