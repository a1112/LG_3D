import json
from pathlib import Path
from typing import Dict

from CoilDataBase import Coil


class SurfaceConfigProperty:
    def __init__(self, surface_config=None):
        self.key = surface_config["key"]
        self.saveFolder = Path(surface_config["saveFolder"])
        self.rotate = surface_config["rotate"]
        self.x_rotate = surface_config["x_rotate"]
        self.direction = surface_config["direction"]
        self.folderList = surface_config["folderList"]
        self.saveImageType = ".png"

    def get_file(self, coil_id, type_):
        return f"{self.saveFolder}/{coil_id}/png/{type_}" + self.saveImageType

    def get_3d_file(self, coil_id):
        return f"{self.saveFolder}/{coil_id}/3D.npy"

    def get_mesh_file(self, coil_id):
        return f"{self.saveFolder}/{coil_id}/meshes/defaultobject_mesh.mesh"

    def get_preview_file(self, coil_id, type_):
        return f"{self.saveFolder}/{coil_id}/preview/{type_}" + self.saveImageType

    def get_mask_file(self, coil_id, type_):
        return f"{self.saveFolder}/{coil_id}/mask/{type_}" + self.saveImageType

    def get_Info(self, coil_id):
        coilState = Coil.getCoilStateByCoilId(coil_id, self.key)
        if coilState:
            return json.loads(Coil.getCoilStateByCoilId(coil_id, self.key).jsonData)

        # jsonFile = self.saveFolder/str(coil_id)/"data.json"
        # with open(jsonFile, "r",encoding="utf-8") as f:
        #     return json.load(f)


def change_path_drive(path, new_drive):
    return str(Path(new_drive) / Path(path.relative_to(path.drive)))


class ServerConfigProperty:
    def __init__(self, server_config=None):
        self.serverConfig = server_config

        def _get_config_(property_, default):
            try:
                return server_config[property_]
            except KeyError:
                return default

        self.surfaceConfigPropertyDict: Dict[str, SurfaceConfigProperty] = {}
        self.useCurrentDerv = _get_config_("useCurrentDerv", False)
        if self.useCurrentDerv:
            drive = Path(__file__).drive
            server_config["saveFolder"] = change_path_drive(self.serverConfig["saveFolder"], drive)
            for surface in self.serverConfig["surface"]:
                for folder in surface["folderList"]:
                    folder["source"] = change_path_drive(folder["source"], folder["source"])
        self.surface = self.serverConfig["surface"]
        for surface in self.surface:
            self.surfaceConfigPropertyDict[surface["key"]] = SurfaceConfigProperty(surface)
        self.balsam_exe = _get_config_("balsam", "balsam.exe")  # balsam.exe 位置
        self.mysqldump_exe = _get_config_("mysqldump", "mysqldump.exe")
        self.colorFromValue = _get_config_("colorFromValue",-700)
        self.colorToValue = _get_config_("colorToValue",700)
        self.colorFromValue_mm = server_config["colorFromValue_mm"]
        self.colorToValue_mm = server_config["colorToValue_mm"]
        self.saveJoinMask = server_config["saveJoinMask"]
        self.max3dSaveThread = server_config["max3dSaveThread"]
        self.downsampleSize = server_config["downsampleSize"]
        self.clip_num = server_config["clip_num"]
        self.max_clip_mun = 500  # serverConfig["max_clip_mun"]

    def get_file(self, coil_id, surface_key, type_, mask=False):
        surface_config = self.surfaceConfigPropertyDict[surface_key]
        if mask:
            return surface_config.get_mask_file(coil_id, type_)
        return surface_config.get_file(coil_id, type_)

    def get_3d_file(self, coil_id, surface_key):
        surface_config = self.surfaceConfigPropertyDict[surface_key]
        return surface_config.get_3d_file(coil_id)

    def get_mesh_file(self, coil_id, surface_key):
        surface_config = self.surfaceConfigPropertyDict[surface_key]
        return surface_config.get_mesh_file(coil_id)

    def get_preview_file(self, coil_id, surface_key, type_):
        surface_config = self.surfaceConfigPropertyDict[surface_key]
        return surface_config.get_preview_file(coil_id, type_)

    def get_info(self, coil_id, surface_key):
        surface_config = self.surfaceConfigPropertyDict[surface_key]
        return surface_config.get_Info(coil_id)

    def to_dict(self):
        res = {}
        for surface in self.serverConfig["surface"]:
            res["surface" + surface["key"]] = surface
        return res
