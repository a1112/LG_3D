"""
    glob objects
    最先初始，  单例
    在多进程中，会存在多个实例，control使用通讯进行同步
"""
from SplicingService import ImageMosaicThread
from utils.ControlManagement import ControlManagement
from utils.ServerMsg import ServerMsg


imageMosaicThread:ImageMosaicThread = None  # 主进程

control = ControlManagement()       # 控制管理

serverMsg=ServerMsg()

