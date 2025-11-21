"""
    glob objects
    鏈€鍏堝垵濮嬶紝  鍗曚緥
    鍦ㄥ杩涚▼涓紝浼氬瓨鍦ㄥ涓疄渚嬶紝control浣跨敤閫氳杩涜鍚屾
"""
import socket

from Base.utils.ControlManagement import ControlManagement, ThreadClass, ProcessClass
from Base.utils.ServerMsg import ServerMsg

ThreadClass = ThreadClass
ProcessClass = ProcessClass

imageMosaicThread = None  # 涓昏繘绋?

control = ControlManagement()  # 鎺у埗绠＄悊

serverMsg = ServerMsg()

