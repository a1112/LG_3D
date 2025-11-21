from .ConfigBase import ConfigBase
from Base.property.Base import DataIntegration

class  LooseCoilConfigItem(ConfigBase):
    def __init__(self, config):
        super().__init__(config)
        self.config = config
        self.name = config["name"]
        self.width = config["width"]
        self.info = config["info"]

        self.camera_map = {}

    def get_config(self):
        return self.name, self.width, self.info

class LooseCoilConfig(ConfigBase):
    def __init__(self, config,data_integration:DataIntegration):

        test={
            "base":{
                "name": "默认判断规则",
                "width": 25,
                "info": "默认判断规则 12点方向两层之间超过6mm认定为松卷"
            }

        }
        config=test
        super().__init__(config)
        self.data_integration = data_integration


    def get_config(self):
        return LooseCoilConfigItem(self.config["base"])
