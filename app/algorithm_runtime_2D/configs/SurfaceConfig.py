
import json
from pathlib import Path

from . import CONFIG
from .BaseConfig import BaseConfig
from .CameraConfig import CameraConfig
from .DebugConfigs import debug_config
from .GlobJoinConfig import GlobalJoinConfigS, GlobalJoinConfigL


class SurfaceConfig(BaseConfig):
    def __init__(self,surface_key, f_):
        self.surface_key = surface_key
        super().__init__(f_)

        self.global_config = GlobalJoinConfigL() if self.surface_key=="L" else GlobalJoinConfigS()
        self.image_size = 5120

        self.camera_configs = [CameraConfig(surface_key,c,self) for c in self.config["cameras"] ]
        clip_config = self.get_value("clip_config", {})
        default_clip_c = 2600 if self.surface_key == "S" else 4000
        self.clip_mode = clip_config.get("mode", "fixed")
        self.clip_fixed = int(clip_config.get("fixed", 200))
        self.clip_dynamic_a = float(clip_config.get("a", 3))
        self.clip_dynamic_b = float(clip_config.get("b", 220))
        self.clip_dynamic_c = float(clip_config.get("c", default_clip_c))
        self.clip_dynamic_offset = int(clip_config.get("offset", 40))
        if CONFIG.DEBUG:
            self.image_size = 1024
            self.save_folder= debug_config.save_folder/surface_key
        else:
            self.save_folder = self.config["save_folder"]

        self.scale = self.image_size / 512

        self.area_copy_to_folder = CONFIG.base_debug_image_save_folder/"area_copy_to_folder"/self.surface_key

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
