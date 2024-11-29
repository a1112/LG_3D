from abc import ABC

from property.Base import DataIntegration


class BaseData(ABC):
    """
    报警基础数据
    """
    def __init__(self,dataIntegration):
        self.dataIntegration:DataIntegration = dataIntegration
