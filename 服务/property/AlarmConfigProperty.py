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

    def getConfig(self):
        return self.name, self.max_width, self.min_width, self.msg


class TaperShapeConfig:
    def __init__(self, config):
        self.config = config
        self.name = config["name"]
        self.height = config["height"]
        self.inner = config["inner"]
        self.outer = config["outer"]
        self.info = config["info"]

    def getConfig(self):
        return self.name, self.height, self.inner, self.outer, self.info


class LooseCoilConfig:
    def __init__(self, config):
        self.config = config
        self.name = config["name"]
        self.width = config["width"]
        self.info = config["info"]

    def getConfig(self):
        return self.name, self.width, self.info


class AlarmConfigProperty:
    def __init__(self, config):
        self.config = config

    def getAlarmFlatRollConfig(self, next_code):
        return AlarmFlatRollConfig(self.config["FlatRoll"][getattr(self.config["FlatRoll"], next_code, "Base")])

    def getTaperShapeConfig(self, next_code):
        return TaperShapeConfig(self.config["TaperShape"][getattr(self.config["TaperShape"], next_code, "Base")])

    def getLooseCoilConfig(self, next_code):
        return LooseCoilConfig(self.config["LooseCoil"][getattr(self.config["LooseCoil"], next_code, "Base")])
