import socket
import sys
from pathlib import Path
import json
import argparse


parser = argparse.ArgumentParser()
parser.add_argument('--config', type=str, default=None, help='相机采集配置文件')
args = parser.parse_args()


CONFIG_DIR = Path("configs")
_GLOB_CONFIG_FOLDER = Path("D:\CONFIG_3D\capture_config")
if _GLOB_CONFIG_FOLDER.exists():
    CONFIG_DIR = _GLOB_CONFIG_FOLDER

isLoc = False
if socket.gethostname() in ["lcx_ace"]:
    isLoc = True

configFile = CONFIG_DIR/r"CapTure.json"

if isLoc:
    configFile = CONFIG_DIR/r"CapTureLoc.json"
elif args.config:
    configFile = Path(args.config)
elif "CapTure" in sys.executable:
    configFile = CONFIG_DIR/fr"{Path(sys.executable).stem}.json"

class CameraConfig(object):
    def __init__(self, config, cap3D = True, cap2D = True):
        self.config = config
        def get_item_config(item,key,default):
            try:
                return item[key]
            except KeyError:
                return default
        if "cap3D" in self.config:
            self.cap3D = self.config["cap3D"]
        else:
            self.cap3D=self.config["cap3D"]=cap3D

        if "cap2D" in self.config:
            self.cap2D = self.config["cap2D"]
        else:
            self.cap2D=self.config["cap2D"]=cap2D
        self.sn = config["sn"]
        self.name=config["name"]
        self.saveFolder= Path(config["saveFolder"])
        self.key=config["key"]
        self.serverIp=config["serverIp"]
        self.serverPort=config["serverPort"]


        self.yaml_config = get_item_config(config,"yaml_config",None)  # 2D 图像 采集的 参数



    def __iter__(self):
        return iter(self.config)

    def __getitem__(self, item):
        return self.config[item]

class CapTureConfig:
    def __init__(self, config_file):
        self.config_file = str(config_file)
        self.config = json.load(open(config_file, 'r'))
        self.signalUrl = self.config["signalUrl"]
        self.SICKGigEVisionTL = str(CONFIG_DIR / r"common/lib/cti/windows_x64/SICKGigEVisionTL.cti")
        self.camera_config_list=[CameraConfig(c) for c in self.config["camera"]]
        self.name_list=[c.name for c in self.camera_config_list]
    def index(self,name):
        try:
            return self.name_list.index(name)
        except ValueError:
            return -1

capTureConfig = CapTureConfig(configFile)

def set_console_mode_none():
    import ctypes
    kernel32 = ctypes.windll.kernel32
    kernel32.SetConsoleMode(kernel32.GetStdHandle(-10), (0x4 | 0x80 | 0x20 | 0x2 | 0x10 | 0x1 | 0x00 | 0x100))
