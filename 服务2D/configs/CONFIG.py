import socket
from pathlib import Path
from threading import Thread

sys_path = Path(fr"D:\CONFIG_3D\configs\area_join.json")
if sys_path.exists():
    CONFIG_FOLDER = sys_path.parent
else:
    CONFIG_FOLDER = Path("config")
JOIN_CONFIG_FILE = CONFIG_FOLDER / "area_join.json"
hostname = socket.gethostname()

WorkClass = Thread

print(hostname)

if hostname == "DESKTOP-94ADH1G":
    DEBUG = True
else:
    DEBUG = False

print(CONFIG_FOLDER)
ModelFolder = CONFIG_FOLDER.parent / "model"