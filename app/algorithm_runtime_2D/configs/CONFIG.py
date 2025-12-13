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

if hostname in ["DESKTOP-3VCH6DO","DESKTOP-94ADH1G"]:
    DEBUG = True
else:
    DEBUG = False

print(CONFIG_FOLDER)
ModelFolder = CONFIG_FOLDER.parent / "model"

base_config_folder = Path(fr"D:\CONFIG_3D")
base_debug_image_save_folder = base_config_folder/"debug"

loger_folder = "../../log"
loger_file = "app_alg_2d.log"

add_to_database=False
