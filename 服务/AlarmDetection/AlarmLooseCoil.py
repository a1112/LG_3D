from property.Base import DataIntegration, DataIntegrationList
from CoilDataBase import Alarm
from property.Data3D import LineData


class AlarmLooseData:
    def __init__(self,lineDatas):
        self.dataIntegrationList=[d[0] for d in lineDatas]
        self.lineDatas=[d[1] for d in lineDatas]
        self.lineDataDicts={}
        for rotate in self.lineDatas[0]:
            # 假设角度一一对应
            self.lineDataDicts[rotate]=[self.lineDatas[0][rotate],self.lineDatas[1][rotate]]

    def detection(self):
        for rotate in self.lineDataDicts:
            lineData1=self.lineDataDicts[rotate][0]
            lineData2=self.lineDataDicts[rotate][1]
            lineData1:LineData
            lineData2:LineData
            print(lineData1.ray_line)
            input()


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
    """
    获取 LineData 数据假设同角度检测
    """
    lineDatas=[]
    for dataIntegration in dataIntegrationList:
        lineDatas.append([dataIntegration,dataIntegration.lineDataDict])
    if len(lineDatas)==2:
        alarmLooseData = AlarmLooseData(lineDatas)
        alarmLooseData.detection()
    else:
        print("暂不支持")
        return