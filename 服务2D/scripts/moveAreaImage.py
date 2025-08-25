
from pathlib import Path
from PIL import Image
import shutil
from tqdm import tqdm

from configs import CONFIG
from configs.DebugConfigs import DebugConfig
from configs.JoinConfig import JoinConfig

join_config = JoinConfig(CONFIG.JOIN_CONFIG_FILE)
max_coil = join_config.get_max_coil()
print(max_coil)



start_coil_id = max_coil - 20000
for i in tqdm(range(start_coil_id, max_coil)):
    for surface_key, surface_config in join_config.surfaces.items():
        url = surface_config.get_area_url(1000)
        move_to_folder = surface_config.area_copy_to_folder/str(i)

        if url.exists():
            move_to_folder.mkdir(parents=True, exist_ok=True)
            shutil.copy(url, move_to_folder)