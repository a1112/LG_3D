import json
from pathlib import Path

jsData = {}
configFilePath = Path("PclServerConfig.json")
if configFilePath.exists():
    jsData = json.load(open("PclServerConfig.json", "r"))


server_ip = "0.0.0.0"
server_port = 1211
plcForwarderUrl = "192.168.0.1"
plcForwarderRack = 0
plcForwarderSlot = 0

if jsData:
    if "server_ip" in jsData:
        server_ip = jsData["server_ip"]
    if "server_port" in jsData:
        server_port = jsData["server_port"]
    if "plc_ip" in jsData:
        plcForwarderUrl = jsData["plc_ip"]
    if "plc_rack" in jsData:
        plcForwarderRack = jsData["plc_rack"]
    if "plc_slot" in jsData:
        plcForwarderSlot = jsData["plc_slot"]
