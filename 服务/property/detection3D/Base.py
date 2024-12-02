from abc import ABC

class BaseData(ABC):
    """
    报警基础数据
    """
    def __init__(self,dataIntegration):
        from ..Base import DataIntegration
        self.dataIntegration:DataIntegration = dataIntegration
