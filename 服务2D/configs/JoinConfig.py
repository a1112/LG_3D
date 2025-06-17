import json
from pathlib import Path

from configs import CONFIG
from .BaseConfig import BaseConfig
from .SurfaceConfig import SurfaceConfig

def sort_folder(image_url_list):
    image_url_list.sort(key=lambda i: int(Path(i).stem),reverse = True)
    return image_url_list

class JoinConfig(BaseConfig):
    def __init__(self, file_):
        super().__init__(file_)
        self.surfaces = {
            surface_key: SurfaceConfig(surface_key,config)
            for surface_key, config in self.config["surfaces"].items()
        }

    def get_max_coil(self):
        if CONFIG.DEBUG:
            return 66000

        surface = list(self.surfaces.values())[0]
        save_folder1 = Path(surface.save_folder)
        folders = list(save_folder1.iterdir())
        folders = sort_folder(folders)
        return folders[0].stem


    def get_last_coil(self):
        if CONFIG.DEBUG:
            return 66000

        surface = list(self.surfaces.values())[0]
        save_folder1 = Path(surface.save_folder)
        folders = list(save_folder1.iterdir())
        folders = sort_folder(folders)
        # folders = folders[start_coil:]
        for f in folders:
            coil_id = f.stem
            if surface.get_area_url(coil_id).exists():
                return coil_id
        return folders[-1].stem

    def can_(self,coil_id):
        coil_id = int(coil_id)
        surface = list(self.surfaces.values())[0]
        if  surface.get_area_url(coil_id).parent.parent.exists() and \
             surface.get_area_url(coil_id+1).parent.parent.exists():
            return True
        return False

