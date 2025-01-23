import socket
from pathlib import Path
import json
import os

from property.AlarmConfigProperty import AlarmConfigProperty
from property.ControlConfigProperty import ControlConfigProperty
from property.DefectClassesProperty import DefectClassesProperty
from property.InfoConfigProperty import InfoConfigProperty
from property.ServerConfigProperty import ServerConfigProperty

# parser = argparse.ArgumentParser()
# parser.add_argument('--config', type=str, default=None, help='3D服务配置文件')
# args = parser.parse_args()


isLoc = False

print(f"主机： {socket.gethostname()}  进程Id {os.getpid()}")
if socket.gethostname() in ["lcx_ace", "lcx_mov", 'DESKTOP-94ADH1G']:
    isLoc = True
base_config_folder = Path(fr"D:\CONFIG_3D")

try:
    file_url=Path(__file__)
    drive_config = Path(file_url.drive) / base_config_folder.relative_to(base_config_folder.drive)
    print(drive_config)
    if drive_config.exists():
        base_config_folder = drive_config
except (NameError,ValueError):
    pass

offline_mode = (Path(base_config_folder)/"offline_mode=true").exists()

if offline_mode:
    from CoilDataBase.config import Config,DeriverList
    Config.deriver = DeriverList.sqlite
    Config.file_url=str(base_config_folder/"Coil.db")
    isLoc = True

def get_file_url(base):
    url = base_config_folder / base
    if not url.exists():
        print(f"{url}不存在！")
        return Path("../CONFIG_3D")/base
    return url

class JsonConfig:
    def __init__(self,base_url):
        self.base_url = base_url
        self.url = get_file_url(base_url)
        with self.url.open("r",encoding="utf-8") as f:
            self.config = json.load(f)

configFile = get_file_url("configs/Server3D.json")
alarmConfigFile = get_file_url( r"configs/Alarm.json")
infoConfigFile = get_file_url( r"configs/Info.json")
controlConfigFile = get_file_url( r"configs/Control.json")
coilClassifiersConfigFile = get_file_url(r"model/CoilClassifiersConfig.json")
defectClassesConfigFile = get_file_url(r"configs/DefectClasses.json")

if isLoc:
    configFile = get_file_url( r"configs/Server3DLoc2.json")
# elif args.config:
#     configFile = Path(args.config)

def set_console_mode():
    import ctypes
    kernel32 = ctypes.windll.kernel32
    kernel32.SetConsoleMode(kernel32.GetStdHandle(-10), (0x4 | 0x80 | 0x20 | 0x2 | 0x10 | 0x1 | 0x00 | 0x100))


if not isLoc:
    set_console_mode()
data_base_api_port = 6011
server_api_port = 6010
image_api_port = 6012
serverConfigProperty = ServerConfigProperty(configFile)
alarmConfigProperty = AlarmConfigProperty(alarmConfigFile)
infoConfigProperty = InfoConfigProperty(infoConfigFile)
defectClassesProperty = DefectClassesProperty(defectClassesConfigFile)
controlConfigProperty = ControlConfigProperty(controlConfigFile)
