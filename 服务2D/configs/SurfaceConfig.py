
import json
from pathlib import Path

from . import CONFIG
from .BaseConfig import BaseConfig
from .CameraConfig import CameraConfig
from .DebugConfigs import debug_config

class SurfaceConfig(BaseConfig):
    def __init__(self,surface_key, f_):
        self.surface_key = surface_key
        super().__init__(f_)
        self.camera_configs = [CameraConfig(surface_key,c) for c in self.config["cameras"] ]
        if CONFIG.DEBUG:
            self.save_folder= debug_config.save_folder/surface_key
        else:
            self.save_folder = self.config["save_folder"]

    def is_run(self):
        return self._run_

    def get_area_url_base(self,coil_id,type_):
        base_folder = Path(self.save_folder)/str(coil_id)
        if CONFIG.DEBUG:
            base_folder.mkdir(parents=True, exist_ok=True)

        return base_folder/type_/"AREA.jpg"

    def get_area_url(self,coil_id):
        return self.get_area_url_base(coil_id,"jpg")

    def get_area_url_pre(self,coil_id):
        return self.get_area_url_base(coil_id,"preview")