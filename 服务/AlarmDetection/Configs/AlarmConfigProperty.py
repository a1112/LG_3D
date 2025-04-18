from pathlib import Path

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

    def get_alarm_flat_roll_config(self):
        return FlatRollConfig(self.config["FlatRoll"])

    def get_taper_shape_config(self):
        return TaperShapeConfig(self.config["TaperShape"])

    def get_loose_coil_config(self):
        return LooseCoilConfig(self.config["LooseCoil"])

    def get_defect_config(self):
        return DefectConfig(self.config["Defect"])

    def get_info_json(self):
        pass