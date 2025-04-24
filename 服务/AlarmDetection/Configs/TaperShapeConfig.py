from .ConfigBase import ConfigBase
from property.Base import DataIntegration


class TaperShapeConfig(ConfigBase):
    def __init__(self, config,data_integration:DataIntegration):
        super().__init__(config)
        self.data_integration = data_integration
        self.name = config["name"]
        self.height = config["height"]
        self.inner = config["inner"]
        self.outer = config["outer"]
        self.info = config["info"]

    def get_config(self):
        return self.name, self.height, self.inner, self.outer, self.info
