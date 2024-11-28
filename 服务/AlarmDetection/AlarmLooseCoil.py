from property.Base import DataIntegration, DataIntegrationList
from CoilDataBase import Alarm


def addAlarmLooseCoil(alarmloose):
    Alarm.addAlarmLooseCoil(alarmloose)

def _detectionAlarmLooseCoil_(dataIntegration: DataIntegration):
    print("_detectionAlarmLooseCoil_")
    for d in dataIntegration.detectionLineData:
        d.dataIntegration=dataIntegration
        d.detection()
        addAlarmLooseCoil(d.getAlarmLooseCoil())

def _detectionAlarmLooseCoilAll_(dataIntegrationList:DataIntegrationList):
    print("_detectionAlarmLooseCoilAll_")
    for dataIntegration in dataIntegrationList:
        _detectionAlarmLooseCoil_(dataIntegration)