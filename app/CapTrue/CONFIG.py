import socket
import sys
from pathlib import Path
import json
import argparse


parser = argparse.ArgumentParser()
parser.add_argument('--config', type=str, default=None, help='相机采集配置文件')
args = parser.parse_args()


CONFIG_DIR = Path("configs")
_GLOB_CONFIG_FOLDER = Path(r"D:\CONFIG_3D\capture_config")
try:
    _global_config_available = _GLOB_CONFIG_FOLDER.exists()
except OSError:
    _global_config_available = False
if _global_config_available:
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
        cap2d_explicit = "cap2D" in self.config
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
        if not cap2d_explicit:
            # A missing area-camera YAML means this position is 3D-only.
            self.cap2D = self.config["cap2D"] = bool(self.yaml_config)



    def __iter__(self):
        return iter(self.config)

    def __getitem__(self, item):
        return self.config[item]

class CapTureConfig:
    def __init__(self, config_file):
        self.config_file = str(config_file)
        with open(config_file, "r", encoding="utf-8") as config_stream:
            self.config = json.load(config_stream)
        self.signalUrl = self.config["signalUrl"]
        self.apiServerIp = self.config.get("apiServerIp", "0.0.0.0")
        self.apiServerPort = int(self.config.get("apiServerPort", 6100))
        cti_path = CONFIG_DIR / r"common/lib/cti/windows_x64/SICKGigEVisionTL.cti"
        try:
            cti_available = cti_path.exists()
        except OSError:
            cti_available = False
        if not cti_available:
            cti_path = (Path(__file__).resolve().parent / "common" / "lib" /
                        "cti" / "windows_x64" / "SICKGigEVisionTL.cti")
        self.SICKGigEVisionTL = str(cti_path)
        self.camera_config_list=[CameraConfig(c) for c in self.config["camera"]]
        self.name_list=[c.name for c in self.camera_config_list]
    def index(self,name):
        try:
            return self.name_list.index(name)
        except ValueError:
            return -1

capTureConfig = CapTureConfig(configFile)

def set_console_mode_none():
    if sys.platform != "win32":
        return False

    import ctypes

    enable_extended_flags = 0x0080
    enable_quick_edit_mode = 0x0040
    std_input_handle = -10
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.GetStdHandle(std_input_handle)
    mode = ctypes.c_uint32()
    if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
        return False

    # Preserve the host's input settings, but explicitly disable QuickEdit.
    # QuickEdit can pause a console process when somebody clicks or selects
    # text in its window.
    new_mode = (mode.value | enable_extended_flags) & ~enable_quick_edit_mode
    return bool(kernel32.SetConsoleMode(handle, new_mode))
