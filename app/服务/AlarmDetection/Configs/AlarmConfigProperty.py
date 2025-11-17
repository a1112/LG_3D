from pathlib import Path


from .FlatRollConfig import FlatRollConfig
from .LooseCoilConfig import LooseCoilConfig
from .TaperShapeConfig import TaperShapeConfig
from .DefectConfig import DefectConfig
from property.BaseConfigProperty import BaseConfigProperty


class AlarmConfigProperty(BaseConfigProperty):
    def __init__(self,file_path: Path):
        super().__init__(file_path)

    def get_alarm_flat_roll_config(self,data_integration):
        return FlatRollConfig(self.config["FlatRoll"],data_integration)

    def get_taper_shape_config(self,data_integration):
        return TaperShapeConfig(self.config["TaperShape"],data_integration)

    def get_loose_coil_config(self,data_integration):
        return LooseCoilConfig(self.config["LooseCoil"],data_integration)

    def get_defect_config(self,data_integration):
        return DefectConfig(self.config["Defect"],data_integration)

    def get_info_json(self):
        pass