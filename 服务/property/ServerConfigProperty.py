import json
from pathlib import Path
from typing import Dict

from CoilDataBase import Coil


class SurfaceConfigProperty:
    def __init__(self, surfaceConfig=None):
        self.key = surfaceConfig["key"]
        self.saveFolder = Path(surfaceConfig["saveFolder"])
        self.rotate = surfaceConfig["rotate"]
        self.x_rotate = surfaceConfig["x_rotate"]
        self.direction = surfaceConfig["direction"]
        self.folderList = surfaceConfig["folderList"]
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


class ServerConfigProperty:
    def __init__(self, serverConfig=None):
        self.serverConfig = serverConfig
        self.surfaceConfigPropertyDict: Dict[str, SurfaceConfigProperty] = {}
        self.surface = self.serverConfig["surface"]
        for surface in self.surface:
            self.surfaceConfigPropertyDict[surface["key"]] = SurfaceConfigProperty(surface)
        self.balsam = serverConfig["balsam"]  # balsam.exe 位置
        self.colorFromValue = serverConfig["colorFromValue"]
        self.colorToValue = serverConfig["colorToValue"]
        self.colorFromValue_mm = serverConfig["colorFromValue_mm"]
        self.colorToValue_mm = serverConfig["colorToValue_mm"]
        self.saveJoinMask = serverConfig["saveJoinMask"]
        self.max3dSaveThread = serverConfig["max3dSaveThread"]
        self.downsampleSize = serverConfig["downsampleSize"]
        self.clip_num = serverConfig["clip_num"]
        self.max_clip_mun = 500  # serverConfig["max_clip_mun"]

    def get_file(self, coil_id, surfaceKey, type_, mask=False):
        surfaceConfig = self.surfaceConfigPropertyDict[surfaceKey]
        if mask:
            return surfaceConfig.get_mask_file(coil_id, type_)
        return surfaceConfig.get_file(coil_id, type_)

    def get_3d_file(self, coil_id, surfaceKey):
        surfaceConfig = self.surfaceConfigPropertyDict[surfaceKey]
        return surfaceConfig.get_3d_file(coil_id)

    def get_mesh_file(self, coil_id, surfaceKey):
        surfaceConfig = self.surfaceConfigPropertyDict[surfaceKey]
        return surfaceConfig.get_mesh_file(coil_id)

    def get_preview_file(self, coil_id, surfaceKey, type_):
        surfaceConfig = self.surfaceConfigPropertyDict[surfaceKey]
        return surfaceConfig.get_preview_file(coil_id, type_)

    def get_Info(self, coil_id, surfaceKey):
        surfaceConfig = self.surfaceConfigPropertyDict[surfaceKey]
        return surfaceConfig.get_Info(coil_id)

    def to_dict(self):
        res = {}
        for surface in self.serverConfig["surface"]:
            res["surface" + surface["key"]] = surface
        return res
