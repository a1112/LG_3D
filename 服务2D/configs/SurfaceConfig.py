
import json
import CONFIG
from .BaseConfig import BaseConfig
from .CameraConfig import CameraConfig


class SurfaceConfig(BaseConfig):
    def __init__(self, f_):
        super().__init__(f_)
        self.camera_configs = [CameraConfig(c) for c in self.config["cameras"] ]
        self.save_folder = self.config["save_folder"]
