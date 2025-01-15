from pathlib import Path

from property.BaseConfigProperty import BaseConfigProperty


class AlarmGradResult:
    def __init__(self, grad, error_msg, config_msg):
        self.grad = grad
        self.errorMsg = error_msg
        self.configMsg = config_msg


class AlarmFlatRollConfig:
    """
    垂直松卷 等级判断
    """

    def __init__(self, config):
        self.config = config
        self.name = config['name']
        self.max_width = config["max"]
        self.min_width = config["min"]
        self.msg = config["info"]

    def get_config(self):
        return self.name, self.max_width, self.min_width, self.msg


class TaperShapeConfig:
    def __init__(self, config):
        self.config = config
        self.name = config["name"]
        self.height = config["height"]
        self.inner = config["inner"]
        self.outer = config["outer"]
        self.info = config["info"]

    def get_config(self):
        return self.name, self.height, self.inner, self.outer, self.info


class LooseCoilConfig:
    def __init__(self, config):
        self.config = config
        self.name = config["name"]
        self.width = config["width"]
        self.info = config["info"]

    def get_config(self):
        return self.name, self.width, self.info


class AlarmConfigProperty(BaseConfigProperty):
    def __init__(self,file_path: Path):
        super().__init__(file_path)

    def get_alarm_flat_roll_config(self, next_code):
        return AlarmFlatRollConfig(self.config["FlatRoll"][getattr(self.config["FlatRoll"], next_code, "Base")])

    def get_taper_shape_config(self, next_code):
        return TaperShapeConfig(self.config["TaperShape"][getattr(self.config["TaperShape"], next_code, "Base")])

    def get_loose_coil_config(self, next_code):
        return LooseCoilConfig(self.config["LooseCoil"][getattr(self.config["LooseCoil"], next_code, "Base")])
