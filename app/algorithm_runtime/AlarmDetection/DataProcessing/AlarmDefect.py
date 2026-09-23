"""Summarize the image-defect detector results for alarm grading."""
from Base.property.Base import DataIntegration, DataIntegrationList
from AlarmDetection.Grading.alarm_defects import grading_alarm_defects

def _detectionAlarmDefect_(dataIntegration: DataIntegration):
    dataIntegration.alarmData.defect_grad_result = None
    result = grading_alarm_defects(dataIntegration)
    dataIntegration.alarmData.defect_grad_result = result
    return result

def _detectionAlarmDefectAll_(dataIntegrationList: DataIntegrationList):
    if isinstance(dataIntegrationList, DataIntegration):
        dataIntegrationList = [dataIntegrationList]
    for data_integration in dataIntegrationList:
        _detectionAlarmDefect_(data_integration)
