"""
    glob objects
    最先初始，  单例
    在多进程中，会存在多个实例，control使用通讯进行同步
"""
import socket

from CONFIG import serverConfigProperty
from utils.ControlManagement import ControlManagement, ThreadClass, ProcessClass
from utils.ServerMsg import ServerMsg

ThreadClass = ThreadClass
ProcessClass = ProcessClass

imageMosaicThread = None  # 主进程

control = ControlManagement()  # 控制管理

serverMsg = ServerMsg()

if socket.gethostname() == "DESKTOP-94ADH1G":
    serverConfigProperty.balsam_exe = fr"C:\Qt\6.8.0\llvm-mingw_64\bin\balsam.exe"
