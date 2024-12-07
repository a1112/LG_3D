
from CONFIG import controlConfig, controlConfigFile
from property.ControlProperty import ControlProperty
from property.WorkerBase import WorkerThreadBase,WorkerProcessBase

ThreadClass = WorkerThreadBase
ProcessClass = WorkerProcessBase

class ControlManagement(ThreadClass):
    def __init__(self):
        super().__init__()
        self.config=controlConfig
        self.configFile=controlConfigFile
        self.ImageSaverWorkNum = 5
        self.minMaskDetectErrorSize=2000    # mask 检测最小报警值
        self.median_filter_size = 3
        self.downsampleSize = 3 # 如果下采样 1，数据将会非常庞大
        self.BaseImageMosaic = ThreadClass
        self.ImageSaverThreadType = "thread"
        self.D3SaverWorkNum = 3
        self.D3SaverThreadType = "multiprocessing"
        self.BaseDataFolder = ProcessClass
        self.baseTimeFormat = "%Y-%m-%d %H:%M:%S"
        self.exportTimeFormat = self.baseTimeFormat
        self.logTimeFormat = self.baseTimeFormat
        self.upperLimit = 75
        self.lowerLimit = -75
        self.leveling_3d=True
        self.save_3d_obj=False

        self.start()

    def get(self):
        return ControlProperty(self.config)

    def getConfig(self):
        return self.config

    def setConfig(self,data):
        self.config.update(data)

    def setProperty(self,key,value):
        self.config[key]=value

    def run(self):
        pass


