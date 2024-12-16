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

offline_mode = True
if offline_mode:
    from CoilDataBase.config import Config,DeriverList
    Config.deriver = DeriverList.sqlite
    Config.file_url=fr"D:\lcx_user\test.db"
    isLoc = True

print(f"主机： {socket.gethostname()}  进程Id {os.getpid()}")
if socket.gethostname() in ["lcx_ace", "lcx_mov", 'DESKTOP-94ADH1G']:
    isLoc = True
base_config_folder = Path("D://CONFIG_3D")

try:
    file_url=Path(__file__)
    drive_config = Path(file_url.drive) / base_config_folder.relative_to(base_config_folder.drive)
    print(drive_config)
    if drive_config.exists():
        base_config_folder = drive_config
except NameError:
    pass
configFile = base_config_folder / "configs/Server3D.json"
alarmConfigFile = base_config_folder / r"configs/Alarm.json"
infoConfigFile = base_config_folder / r"configs/Info.json"
controlConfigFile = base_config_folder / r"configs/Control.json"

if isLoc:
    configFile = base_config_folder / r"configs/Server3DLoc2.json"
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


def set_console_mode():
    import ctypes
    kernel32 = ctypes.windll.kernel32
    kernel32.SetConsoleMode(kernel32.GetStdHandle(-10), (0x4 | 0x80 | 0x20 | 0x2 | 0x10 | 0x1 | 0x00 | 0x100))


if not isLoc:
    set_console_mode()

data_base_api_port = 6011
server_api_port = 6010
image_api_port = 6012
