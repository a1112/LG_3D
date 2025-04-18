class LooseCoilConfig:
    def __init__(self, config):
        self.config = config
        self.name = config["name"]
        self.width = config["width"]
        self.info = config["info"]

    def get_config(self):
        return self.name, self.width, self.info
