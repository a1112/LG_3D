from .ConfigBase import ConfigBase


class DefectConfig(ConfigBase):
    # 缺陷 级别判断
    def __init__(self, config):
        super().__init__(config)
