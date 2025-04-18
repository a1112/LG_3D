from .ConfigBase import ConfigBase


class FlatRollConfig(ConfigBase):
    """
    垂直松卷 等级判断
    """
    def __init__(self, config):
        super().__init__(config)
        self.name = config['name']
        self.max_width = config["max"]
        self.min_width = config["min"]
        self.msg = config["info"]

    def get_config(self):
        return self.name, self.max_width, self.min_width, self.msg
