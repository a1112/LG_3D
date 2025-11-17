from .ConfigBase import ConfigBase
from property.Base import DataIntegration

class TaperShapeConfigItem(ConfigBase):
    def __init__(self, config):
        super().__init__(config)
        self.config = config
        self.name = config["name"]
        self.height = config["height"]
        self.inner = config["inner"]
        self.outer = config["outer"]
        self.info = config["info"]

    def get_config(self):
        return self.name, self.height, self.inner, self.outer, self.info

class TaperShapeConfig(ConfigBase):
    def __init__(self, config,data_integration:DataIntegration):
        test = {
            "msg":"塔形检测",

            "base": {
                "name": "默认判断规则",
                "height": [60, 80],
                "inner": 80,
                "outer": 80,
                "info": "默认判断规则 溢出边60"
            },
            "configs":[
            ]
        }
        config = test


        super().__init__(config)
        self.data_integration = data_integration



    def get_config(self):
        return TaperShapeConfigItem(self.config["base"])
