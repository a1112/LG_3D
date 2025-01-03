"""
    glob objects
    最先初始，  单例
    在多进程中，会存在多个实例，control使用通讯进行同步
"""
from CONFIG import ServerConfig, alarmConfig, infoConfig
from property.AlarmConfigProperty import AlarmConfigProperty
from property.InfoConfigProperty import InfoConfigProperty
from property.ServerConfigProperty import ServerConfigProperty
from property.DefectClassesProperty import DefectClassesProperty
from utils.ControlManagement import ControlManagement, ThreadClass, ProcessClass
from utils.ServerMsg import ServerMsg

ThreadClass = ThreadClass
ProcessClass = ProcessClass

imageMosaicThread = None  # 主进程

control = ControlManagement()  # 控制管理

serverMsg = ServerMsg()
serverConfigProperty = ServerConfigProperty(ServerConfig)
alarmConfigProperty = AlarmConfigProperty(alarmConfig)
infoConfigProperty = InfoConfigProperty(infoConfig)
defectClassesProperty = DefectClassesProperty()
