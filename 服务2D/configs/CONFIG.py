import socket
from pathlib import Path
from threading import Thread
sys_path = Path(fr"D:\CONFIG_3D\configs\area_join.json")
if sys_path.exists():
    CONFIG_FOLDER = sys_path.parent
else:
    CONFIG_FOLDER = Path("config")
JOIN_CONFIG_FILE = CONFIG_FOLDER / "area_join.json"

WorkClass = Thread

DEBUG = True