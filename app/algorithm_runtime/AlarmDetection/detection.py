from .DataProcessing.TaperShape import _detection_taper_shape_all_
from .DataProcessing.AlarmLooseCoil import _detectionAlarmLooseCoilAll_
from .DataProcessing.AlarmDefect import _detectionAlarmDefectAll_
from .DataProcessing.AlarmFlatRoll import _detectionAlarmFlatRollAll_

from utils.DetectionSpeedRecord import DetectionSpeedRecord

from .Grading.CoilGrading import grading, grading_all
from Base.utils.Log import logger
from Base.property.Base import DataIntegration
from .Result.errors import alarm_error_result, merge_alarm_errors, record_alarm_error


def _run_alarm_stage(label, stage, data_integration_list):
    try:
        return stage(data_integration_list)
    except Exception as e:
        coil_ids = [
            getattr(data, "coilId", None) for data in data_integration_list
        ]
        logger.exception("alarm stage failed stage=%s coils=%s error=%s",
                         label, coil_ids, e)
        for data in data_integration_list:
            record_alarm_error(data, label, e)
    return {}


@DetectionSpeedRecord.timing_decorator("判级时间")
def detection_all(
        data_integration_list):  #  Union[DataIntegrationList, DataIntegration]
    """
    判级
    """
    # The legacy integration containers are stateful iterators. Materialize
    # once so an exception on one surface cannot consume the next stage's
    # input or leave the second surface unprocessed.
    if isinstance(data_integration_list, DataIntegration):
        data_integration_list = [data_integration_list]
    else:
        data_integration_list = list(data_integration_list)
    for data in data_integration_list:
        data.alarm_processing_errors = []
    errors = {}
    stages = (
        ("flat_roll", _detectionAlarmFlatRollAll_),
        ("taper_shape", _detection_taper_shape_all_),
        ("loose_coil", _detectionAlarmLooseCoilAll_),
        ("defect", _detectionAlarmDefectAll_),
        ("grading", grading_all),
    )
    for label, stage in stages:
        for data_integration in data_integration_list:
            result = _run_alarm_stage(label, stage, [data_integration])
            merge_alarm_errors(errors, result)
            merge_alarm_errors(errors, alarm_error_result(data_integration))
    return errors

    # for dataIntegration in dataIntegrationList:
    #
    #     for alarmTaperShape in dataIntegration.alarmTaperShapeList:
    #         addAlarmTaperShape(dataIntegration, alarmTaperShape)
