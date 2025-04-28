from typing import Optional, Dict

from CoilDataBase import Alarm

from property.Data3D import LineData
from .FlatRollData import FlatRollData


class AlarmData:

    def __init__(self,data_integration):
        self.data_integration = data_integration
        self.flatRollData: Optional[FlatRollData] = None
        self.lineDataDict:Optional[Dict[LineData]] = None

    def set_flat_roll_data(self,flat_roll_data):
        self.flatRollData = flat_roll_data

    def commit(self):
        self.flatRollData.commit()

        line_data_dict = self.lineDataDict
        model_list = []
        for lineData in line_data_dict.values():
            try:
                model_list.append(lineData.line_data_model(self.data_integration))
                model_list.extend(lineData.all_point_data_model(self.data_integration))
            except AttributeError as e:
                print(e)
        Alarm.addObj(model_list)

    def set_line_data_dict(self, line_data):
        self.lineDataDict = line_data