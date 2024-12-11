import socket
import sys
from pathlib import Path
import json
import argparse


parser = argparse.ArgumentParser()
parser.add_argument('--config', type=str, default=None, help='相机采集配置文件')
args = parser.parse_args()


isLoc = False
if socket.gethostname() in ["lcx_ace"]:
    isLoc = True

configFile = Path(r"configs/CapTure.json")

if isLoc:
    configFile = Path(r"configs/CapTureLoc.json")
elif args.config:
    configFile = Path(args.config)
elif "CapTure" in sys.executable:
    configFile = Path(fr"configs/{Path(sys.executable).stem}.json")

class CameraConfig(object):
    def __init__(self, config):
        self.config = config
        self.sn = config["sn"]
        self.name=config["name"]
        self.saveFolder= Path(config["saveFolder"])
        self.key=config["key"]
        self.serverIp=config["serverIp"]
        self.serverPort=config["serverPort"]

    def __iter__(self):
        return iter(self.config)

    def __getitem__(self, item):
        return self.config[item]

class CapTureConfig:
    def __init__(self, config_file):
        self.config_file = str(config_file)
        self.config = json.load(open(config_file, 'r'))
        self.signalUrl = self.config["signalUrl"]
        self.SICKGigEVisionTL = str(Path(r"common/lib/cti/windows_x64/SICKGigEVisionTL.cti"))
        self.camera_config_list=[CameraConfig(c) for c in self.config["camera"]]
        self.name_list=[c.name for c in self.camera_config_list]
    def index(self,name):
        try:
            return self.name_list.index(name)
        except ValueError:
            return -1

capTureConfig = CapTureConfig(configFile)
