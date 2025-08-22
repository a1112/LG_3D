
from pathlib import Path
from PIL import Image

from configs import CONFIG
from configs.JoinConfig import JoinConfig

JoinConfig = JoinConfig(CONFIG.JOIN_CONFIG_FILE)


for surface_key, surface_config in JoinConfig.surfaces:
    surface_config