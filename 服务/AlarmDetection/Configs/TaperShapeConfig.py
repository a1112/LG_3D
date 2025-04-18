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
