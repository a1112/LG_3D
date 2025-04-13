import json
from configs import CONFIG
from .BaseConfig import BaseConfig
from .SurfaceConfig import SurfaceConfig


class JoinConfig(BaseConfig):
    def __init__(self, file_):
        super().__init__(file_)
        self.surfaces = {
            surface_key: SurfaceConfig(config)
            for surface_key, config in self.config["surfaces"].items()
        }


join_config = JoinConfig(CONFIG.JOIN_CONFIG_FILE)
