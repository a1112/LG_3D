from collections.abc import Mapping
from typing import Optional, Dict

from CoilDataBase import Alarm

from Base.property.Data3D import LineData
from Base.utils.Log import logger
from .FlatRollData import FlatRollData


class AlarmData:

    def __init__(self,data_integration):
        self.data_integration = data_integration
        self.flatRollData: Optional[FlatRollData] = None
        self.lineDataDict:Optional[Dict[LineData]] = None
        self.taper_shape_disabled = False
        self.taper_shape_errors = []
        self.taper_shape_grading_errors = []

    def set_flat_roll_data(self,flat_roll_data):
        self.flatRollData = flat_roll_data

    def _commit_flat_roll_data(self):
        if self.flatRollData is None:
            logger.warning("skip missing flat roll data before taper line commit")
            return
        try:
            self.flatRollData.commit()
        except (AttributeError, TypeError, ValueError, IndexError, OverflowError) as e:
            logger.warning(f"skip invalid flat roll data before taper line commit: {e}")

    def commit(self):
        self._commit_flat_roll_data()

        line_data_dict = self.lineDataDict or {}
        model_list = []
        if isinstance(line_data_dict, Mapping):
            line_data_values = line_data_dict.values()
        elif isinstance(line_data_dict, (list, tuple, set)):
            line_data_values = line_data_dict
        else:
            logger.warning(f"skip invalid taper line data container: {type(line_data_dict).__name__}")
            line_data_values = []
        for lineData in line_data_values:
            try:
                model_list.append(lineData.line_data_model(self.data_integration))
                model_list.extend(lineData.all_point_data_model(self.data_integration))
            except (AttributeError, TypeError, ValueError, IndexError, OverflowError) as e:
                logger.warning(f"skip invalid taper line data: {e}")
        if model_list:
            Alarm.addObj(model_list)

    def set_line_data_dict(self, line_data):
        self.lineDataDict = line_data or {}
