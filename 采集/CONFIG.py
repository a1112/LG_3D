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

captureConfigFile = str(configFile)
SICKGigEVisionTL = str(Path(r"common/lib/cti/windows_x64/SICKGigEVisionTL.cti"))


CapTureConfig = json.load(open(captureConfigFile, 'r'))
SignalUrl = CapTureConfig["signalUrl"]
