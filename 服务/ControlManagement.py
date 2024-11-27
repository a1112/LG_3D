
import threading
from multiprocessing import Process
from threading import Thread
from property.ControlProperty import ControlProperty
from CONFIG import controlConfig, controlConfigFile

ThreadClass = Thread
ProcessClass = Process

BaseImageMosaic=threading.Thread

ImageSaverWorkNum=3
ImageSaverThreadType="thread"

D3SaverWorkNum=3
D3SaverThreadType="multiprocessing"

BaseDataFolder=ProcessClass

class ControlManagement:
    def __init__(self):
        self.config=controlConfig
        self.configFile=controlConfigFile

        self.minMaskDetectErrorSize=2000    # mask 检测最小报警值

    def get(self):
        return ControlProperty(self.config)

    def getConfig(self):
        return self.config

    def setConfig(self,data):
        self.config.update(data)

    def setProperty(self,key,value):
        self.config[key]=value

control = ControlManagement()