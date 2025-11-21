"""
    glob objects
    最先初始，  单例
    在多进程中，会存在多个实例，control使用通讯进行同步
"""
import socket

from Base.utils.ControlManagement import ControlManagement, ThreadClass, ProcessClass
from Base.utils.ServerMsg import ServerMsg

ThreadClass = ThreadClass
ProcessClass = ProcessClass

imageMosaicThread = None  # 主进程

control = ControlManagement()  # 控制管理

serverMsg = ServerMsg()

