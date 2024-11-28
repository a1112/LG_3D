class AlarmGradResult:
    def __init__(self,grad, errorMsg,configMsg):
        self.grad = grad
        self.errorMsg = errorMsg
        self.configMsg = configMsg

class AlarmFlatRollConfig:
    """
    垂直松卷 等级判断
    """
    def __init__(self, config):
        self.config = config
        self.name = config['name']
        self.max_width=config["max"]
        self.min_width=config["min"]
        self.msg=config["info"]

    def getConfig(self):
        return self.name,self.max_width, self.min_width, self.msg


class TaperShapeConfig:
    def __init__(self, config):
        self.config = config
        self.name = config["name"]
        self.height=config["height"]
        self.inner=config["inner"]
        self.outer=config["outer"]
        self.info=config["info"]

    def getConfig(self):
        return self.name, self.height, self.inner, self.outer, self.info


class LooseCoilConfig:
    def __init__(self, config):
        self.config = config
        self.name = config["name"]
        self.width=config["width"]
        self.info=config["info"]

    def getConfig(self):
        return self.name,self.width, self.info



class AlarmConfigProperty:
    def __init__(self, config):
        self.config = config

    def getAlarmFlatRollConfig(self,nextCode):
        return AlarmFlatRollConfig(self.config["FlatRoll"][getattr(self.config["FlatRoll"],nextCode,"Base")])

    def getTaperShapeConfig(self,nextCode):
        return TaperShapeConfig(self.config["TaperShape"][getattr(self.config["TaperShape"],nextCode,"Base")])

    def getLooseCoilConfig(self,nextCode):
        return LooseCoilConfig(self.config["LooseCoil"][getattr(self.config["LooseCoil"],nextCode,"Base")])


