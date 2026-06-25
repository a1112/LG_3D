import os
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

if hostname in ["DESKTOP-3VCH6DO", "DESKTOP-94ADH1G"]:
    DEBUG = True
else:
    DEBUG = False

print(CONFIG_FOLDER)
ModelFolder = CONFIG_FOLDER.parent / "model"

base_config_folder = Path(fr"D:\CONFIG_3D")
base_debug_image_save_folder = base_config_folder / "debug"

loger_folder = "../../log"
loger_file = "app_alg_2d.log"


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


add_to_database = _env_bool("ALG_2D_ADD_TO_DATABASE", True)
area_detection_tile_size = _env_int("ALG_2D_AREA_DETECTION_TILE_SIZE", 1024)
area_detection_image_size = _env_int("ALG_2D_AREA_DETECTION_IMAGE_SIZE", area_detection_tile_size)
enable_classifier = _env_bool("ALG_2D_ENABLE_CLASSIFIER", True)
classifier_config = os.getenv("ALG_2D_CLASSIFIER_CONFIG")
classifier_crop_margin = _env_int("ALG_2D_CLASSIFIER_CROP_MARGIN", 5)
classifier_crop_min_size = _env_int("ALG_2D_CLASSIFIER_CROP_MIN_SIZE", 60)
