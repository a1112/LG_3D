from .ConfigBase import ConfigBase
from property.Base import DataIntegration


class LooseCoilConfig(ConfigBase):
    def __init__(self, config,data_integration:DataIntegration):
        super().__init__(config)
        self.data_integration = data_integration
        self.name = config["name"]
        self.width = config["width"]
        self.info = config["info"]

    def get_config(self):
        return self.name, self.width, self.info
