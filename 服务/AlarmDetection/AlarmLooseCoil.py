from property.Base import DataIntegration
from CoilDataBase import Alarm


def addAlarmLooseCoil(alarmloose):
    Alarm.addAlarmLooseCoil(alarmloose)

def _detectionAlarmLooseCoil_(dataIntegration: DataIntegration):
    print("_detectionAlarmLooseCoil_")
    for d in dataIntegration.detectionLineData:
        d.dataIntegration=dataIntegration
        d.detection()
        addAlarmLooseCoil(d.getAlarmLooseCoil())
