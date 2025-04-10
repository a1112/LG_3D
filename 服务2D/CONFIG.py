from pathlib import Path
from threading import Thread

CONFIG_FOLDER = Path("./config")


JOIN_CONFIG_FILE = CONFIG_FOLDER / "area_join.json"

WorkClass = Thread