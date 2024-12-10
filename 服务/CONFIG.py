import socket
from pathlib import Path
import json
import os

# parser = argparse.ArgumentParser()
# parser.add_argument('--config', type=str, default=None, help='3D服务配置文件')
# args = parser.parse_args()

RendererList = ["JET"]

SaveImageType = ".png"

isLoc = False
print(f"主机： {socket.gethostname()}  进程Id {os.getpid()}")
if socket.gethostname() in ["lcx_ace", "lcx_mov", 'DESKTOP-94ADH1G']:
    isLoc = True
BaseConfigFolder = Path("D://CONFIG_3D")

configFile = BaseConfigFolder / "configs/Server3D.json"
alarmConfigFile = BaseConfigFolder / r"configs/Alarm.json"
infoConfigFile = BaseConfigFolder / r"configs/Info.json"
controlConfigFile = BaseConfigFolder / r"configs/Control.json"

if isLoc:
    configFile = BaseConfigFolder / r"configs/Server3DLoc2.json"
# elif args.config:
#     configFile = Path(args.config)

ServerConfig = json.load(open(configFile, 'r', encoding="utf-8"))
alarmConfig = json.load(open(alarmConfigFile, 'r', encoding="utf-8"))
infoConfig = json.load(open(infoConfigFile, 'r', encoding="utf-8"))
controlConfig = json.load(open(controlConfigFile, 'r', encoding="utf-8"))

VERSION = [0, 1, 11]
VERSION_String = ".".join([str(i) for i in VERSION])
if socket.gethostname() == "DESKTOP-94ADH1G":
    ServerConfig["balsam"] = fr"C:\Qt\6.8.0\llvm-mingw_64\bin\balsam.exe"


def setConsoleMode():
    import ctypes
    kernel32 = ctypes.windll.kernel32
    kernel32.SetConsoleMode(kernel32.GetStdHandle(-10), (0x4 | 0x80 | 0x20 | 0x2 | 0x10 | 0x1 | 0x00 | 0x100))


if not isLoc:
    setConsoleMode()

dataBaseApiPort = 6011
serverApiPort = 6010
imageApiport = 6012
