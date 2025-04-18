from pathlib import Path
import json
from typing import List
from pathlib import WindowsPath

import CONFIG
from .BaseConfig import BaseConfig

class CameraConfig(BaseConfig):
    def __init__(self, file_):
        super().__init__(file_)
        self.folder = Path(self.config["folder"])
        self.key = Path(self.folder.as_uri()).name
        self.loss_num = self.get_value("loss_num",0)
        self.max_len = self.get_value("max_len",10)

    def get_folder(self,coil_id):
        return self.folder/str(coil_id)/"area"

    def is_run(self):
        return True
        return self.key in ["Cap_S_M"]

    def get_url_list(self, url_list:List[WindowsPath]):
        url_list = url_list[self.loss_num:self.loss_num+self.max_len]
        if "S" in self.key:
            url_list = url_list[::-1]
        return url_list

    # Cap_S_U
    # Cap_S_M
    # Cap_S_D
    # Cap_L_U
    # Cap_L_M
    # Cap_L_D