from property.Base import DataIntegration
from .ConfigBase import ConfigBase


class DefectConfig(ConfigBase):
    # 缺陷 级别判断
    def __init__(self, config,data_integration:DataIntegration):
        super().__init__(config)
        self.data_integration = data_integration
