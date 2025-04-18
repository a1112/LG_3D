from typing import Union

from CoilDataBase.models import AlarmLooseCoil
from property.Base import DataIntegration, DataIntegrationList
from property.Data3D import LineData
from CoilDataBase.Alarm import addAlarmLooseCoil
import numpy as np


# Function to group consecutive rows
def group_consecutive(arr):
    groups = []
    current_group = [arr[0]] if arr.size > 0 else []

    for i in range(1, len(arr)):
        if arr[i, 0] == arr[i - 1, 0] + 1:  # Check if consecutive
            current_group.append(arr[i])
        else:
            groups.append(np.array(current_group))
            current_group = [arr[i]]

    if current_group:
        groups.append(np.array(current_group))  # Append the last group

    return groups


class AlarmLooseData:
    def __init__(self, lineDatas):
        self.dataIntegrationList = [d[0] for d in lineDatas]
        self.lineDatas = [d[1] for d in lineDatas]
        self.lineDataDicts = {}
        for rotate in self.lineDatas[0]:
            # 假设角度一一对应
            self.lineDataDicts[rotate] = [self.lineDatas[0][rotate], self.lineDatas[1][rotate]]

    def detection(self):
        for rotate in self.lineDataDicts:
            lineData1 = self.lineDataDicts[rotate][0]
            lineData2 = self.lineDataDicts[rotate][1]
            lineData1: LineData
            lineData2: LineData
            ray1 = lineData1.ray_line_mm
            ray2 = lineData2.ray_line_mm
            # print(lineData1.zero_mm)
            # print(ray1.shape)
            # print(ray2.shape)
            # print(ray1)
            lineData1.none_data_sub
            lineData2.none_data_sub
            # print(lineData1.none_data_sub)
            # print(lineData2.none_data_sub)
            # # grouped_subsegments = group_consecutive(subsegment)
            # # oldHasdata = False
            # # for index,point in enumerate(ray1):
            # #     hasData=lineData1.mmNoneData(point[2])
            # input()


def _detectionAlarmLooseCoil_(data_integration: DataIntegration):
    for d in data_integration.detectionLineData:
        d.dataIntegration = data_integration
        d.detection()
        addAlarmLooseCoil(d.get_alarm_loose_coil())


def _detectionAlarmLooseCoilAll_(data_integration_list: Union[DataIntegrationList, DataIntegration]):
    """
    获取 LineData 数据假设同角度检测
    """
    line_datas = []
    for dataIntegration in data_integration_list:
        line_datas.append([dataIntegration, dataIntegration.lineDataDict])
        addAlarmLooseCoil(AlarmLooseCoil(
            secondaryCoilId = dataIntegration.coilId,
            surface=dataIntegration.surface,
            max_width=5,
            rotation_angle=0

        ))

    if len(line_datas) == 2:
        alarm_loose_data = AlarmLooseData(line_datas)
        alarm_loose_data.detection()
    else:
        print("暂不支持")
        return
