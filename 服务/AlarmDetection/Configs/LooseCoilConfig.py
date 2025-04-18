from .ConfigBase import ConfigBase

class LooseCoilConfig(ConfigBase):
    def __init__(self, config):
        super().__init__(config)
        self.name = config["name"]
        self.width = config["width"]
        self.info = config["info"]

    def get_config(self):
        return self.name, self.width, self.info
