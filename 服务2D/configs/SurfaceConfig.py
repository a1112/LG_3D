
import json
from pathlib import Path

import CONFIG
from .BaseConfig import BaseConfig
from .CameraConfig import CameraConfig


class SurfaceConfig(BaseConfig):
    def __init__(self, f_):
        super().__init__(f_)
        self.camera_configs = [CameraConfig(c) for c in self.config["cameras"] ]
        self.save_folder = self.config["save_folder"]

    def get_area_url_base(self,coil_id,type_):
        return Path(self.save_folder)/str(coil_id)/type_/"AREA.jpg"

    def get_area_url(self,coil_id):
        return self.get_area_url_base(coil_id,"jpg")

    def get_area_url_pre(self,coil_id):
        return self.get_area_url_base(coil_id,"preview")