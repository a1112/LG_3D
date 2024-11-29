
import threading
from multiprocessing import Process
from threading import Thread

from CONFIG import controlConfig, controlConfigFile
from property.ControlProperty import ControlProperty

ThreadClass = Thread
ProcessClass = Process

class ControlManagement(threading.Thread):
    def __init__(self):
        super().__init__()
        self.config=controlConfig
        self.configFile=controlConfigFile
        self.ImageSaverWorkNum = 5
        self.minMaskDetectErrorSize=2000    # mask 检测最小报警值
        self.median_filter_size = 3
        self.downsampleSize = 1
        self.BaseImageMosaic = threading.Thread
        self.ImageSaverThreadType = "thread"
        self.D3SaverWorkNum = 3
        self.D3SaverThreadType = "multiprocessing"
        self.BaseDataFolder = ProcessClass
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


