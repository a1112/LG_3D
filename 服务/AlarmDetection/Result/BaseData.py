from abc import ABC

class BaseData(ABC):
    """
    报警基础数据
    """
    def __init__(self,dataIntegration):
        self.dataIntegration = dataIntegration
