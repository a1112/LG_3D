from pathlib import Path

from AlarmDetection.Configs.AlarmFlatRollConfig import AlarmFlatRollConfig
from AlarmDetection.Configs.LooseCoilConfig import LooseCoilConfig
from AlarmDetection.Configs.TaperShapeConfig import TaperShapeConfig
from property.BaseConfigProperty import BaseConfigProperty


class AlarmGradResult:
    def __init__(self, grad, error_msg, config_msg):
        self.grad = grad
        self.errorMsg = error_msg
        self.configMsg = config_msg


class AlarmConfigProperty(BaseConfigProperty):
    def __init__(self,file_path: Path):
        super().__init__(file_path)

    def get_alarm_flat_roll_config(self, next_code):
        return AlarmFlatRollConfig(self.config["FlatRoll"][getattr(self.config["FlatRoll"], next_code, "Base")])

    def get_taper_shape_config(self, next_code):
        return TaperShapeConfig(self.config["TaperShape"][getattr(self.config["TaperShape"], next_code, "Base")])

    def get_loose_coil_config(self, next_code):
        return LooseCoilConfig(self.config["LooseCoil"][getattr(self.config["LooseCoil"], next_code, "Base")])

    def get_info_json(self):
        pass