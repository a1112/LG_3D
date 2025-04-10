from pathlib import Path
import json
import CONFIG
from .BaseConfig import BaseConfig

class CameraConfig(BaseConfig):
    def __init__(self, file_):
        super().__init__(file_)
        self.folder = Path(self.config["folder"])

    def get_folder(self,coil_id):
        return self.folder/str(coil_id)/"area"

    def is_run(self):
        return True