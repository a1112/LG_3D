from pathlib import Path

from property.Base import DataIntegration
from .FlatRollConfig import FlatRollConfig
from .LooseCoilConfig import LooseCoilConfig
from .TaperShapeConfig import TaperShapeConfig
from .DefectConfig import DefectConfig
from property.BaseConfigProperty import BaseConfigProperty


class AlarmGradResult:
    def __init__(self, grad, error_msg, config_msg):
        self.grad = grad
        self.errorMsg = error_msg
        self.configMsg = config_msg


class AlarmConfigProperty(BaseConfigProperty):
    def __init__(self,file_path: Path):
        super().__init__(file_path)

    def get_alarm_flat_roll_config(self,data_integration: DataIntegration):
        return FlatRollConfig(self.config["FlatRoll"],data_integration)

    def get_taper_shape_config(self,data_integration: DataIntegration):
        return TaperShapeConfig(self.config["TaperShape"],data_integration)

    def get_loose_coil_config(self,data_integration: DataIntegration):
        return LooseCoilConfig(self.config["LooseCoil"],data_integration)

    def get_defect_config(self,data_integration: DataIntegration):
        return DefectConfig(self.config["Defect"],data_integration)

    def get_info_json(self):
        pass