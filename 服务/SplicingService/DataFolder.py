import json

from pathlib import Path
import time

import cv2
import numpy as np
from PIL import Image
from CONFIG import isLoc
from Globs import serverConfigProperty
from SplicingService.DataFolderLog import DataFolderLog
from tools.Glob import cmdThread

from tools import tool
from tools.data3dTool import auto_data_leveling_3d

from utils import Log
import Globs
from property.Types import LevelingType

logger = Log.logger


class DataFolder(Globs.control.BaseDataFolder):
    def __init__(self, fd, logger_process):
        super().__init__()
        self.coilAreaModel = None
        self.loggerProcess = logger_process
        print("self.loggerProcess",self.loggerProcess)
        self.saveMaskFolder = None
        self.saveMask = None
        self.imageMosaicList = None
        # fd = json.loads(fd)
        folder_config, save_folder, direction = fd
        self.direction = direction  # "L"
        self.saveFolder = Path(save_folder)
        self.folderConfig = folder_config
        self.source = Path(folder_config["source"])
        self.folderName = self.source.stem
        self.cropLeft = folder_config["cropLeft"]
        self.cropRight = folder_config["cropRight"]

        self.start()

    def check_detection_end(self, coil_id):
        return self.static_check_detection_end(self.source, coil_id)

    @staticmethod
    def static_check_detection_end(source, coilId):
        source = source / str(coilId) / "2D"
        if not source.exists():
            return False
        bmpList = list(source.glob("*.bmp"))
        if len(list(bmpList)) < 5:
            return False
        for bmp in bmpList:
            file_time = bmp.stat().st_mtime
            if time.time() - file_time < 5:
                return False
        return True

    def get_data(self):
        return self.consumer.get()

    def set_coil_id(self, coil_id):
        self.producer.put(coil_id)

    def mk_link(self, coil_id):
        link_folder = self.saveFolder / coil_id / "link"
        link_folder.mkdir(parents=True, exist_ok=True)
        # os.link(link_folder / self.folderName, self.source / coilId)
        cmd = fr"mklink /D {link_folder / self.folderName} {self.source / coil_id}"
        cmdThread.put(cmd)

    def load_json(self, coil_id):
        source_json = self.source / coil_id / "json"
        source_json_list = list(source_json.glob("*.json"))
        source_json_list.sort(key=lambda x: int(x.stem))
        json_datas = []
        for i in range(len(source_json_list)):
            with open(source_json_list[i], 'r') as f:
                json_datas.append(json.load(f))
        stem_list = [data.stem for data in source_json_list]
        timestamp_list = [data["timestamp"] // 10e7 for data in json_datas]
        timestamp_list_differ = []
        for i in range(len(timestamp_list) - 1):
            timestamp_list_differ.append(timestamp_list[i + 1] - timestamp_list[i])
        maxVal = max(timestamp_list_differ)
        if maxVal > 200:
            maxIndex = timestamp_list_differ.index(maxVal)
            if maxIndex < len(timestamp_list_differ) - 5:
                stem_list = stem_list[maxIndex + 1:]
                json_datas = json_datas[maxIndex + 1:]
        return json_datas, stem_list

    def load2_d(self, coil_id, stem_list):
        source2_d = self.source / coil_id / "2D"
        images = []
        for stem in stem_list:
            image_f = source2_d / (stem + ".bmp")
            if not image_f.exists():
                image_f = source2_d / (stem + ".jpg")
            with Image.open(image_f) as image:
                images.append(np.array(image))
        join_image = np.vstack(images)
        cv_image, mask, rec = tool.autoCrop(self.folderName, join_image, [self.cropLeft, self.cropRight], self.direction)
        steel_rec = self.coilAreaModel.getSteelRect(Image.fromarray(cv_image))
        return cv_image, mask, rec, steel_rec

    def load3_d(self, coilId, rec, stem_list, json_data_list):
        source3_d = self.source / coilId / "3D"
        npyList = []
        for stem, jsData in zip(stem_list, json_data_list):
            npyF = source3_d / (stem + ".npy")
            if not npyF.exists():
                npzF = source3_d / (stem + ".npz")
                npy = np.load(npzF)["array"]
            else:
                npy = np.load(npyF)
            npyList.append(npy)
        npy = np.vstack(npyList)
        if rec:
            npy = npy[:, rec[0]:rec[0] + rec[2]]
        return npy

    def has_data(self, coil_id):
        return self.static_has_data(self.source, coil_id)

    @staticmethod
    def static_has_data(source, coil_id):
        source = Path(source)
        exists = (source / coil_id).exists()
        if not exists:
            logger.error(f"DataFolder {coil_id} does not exist.  {source / coil_id}")
        return exists

    def run(self):
        self.imageMosaicList = []
        self.saveMask = serverConfigProperty.saveJoinMask
        if self.saveMask:
            self.saveMaskFolder = self.source.parent / "SaveMask" / self.folderName
            self.saveMaskFolder.mkdir(parents=True, exist_ok=True)

        from alg.CoilMaskModel import CoilAreaModel
        self.coilAreaModel = CoilAreaModel()
        while True:
            coilId = self.producer.get()
            # logger.info(f"DataFolder {coilId} start")
            data = {}
            # dataFolderLog = DataFolderLog(self)
            try:
                jsonDatas, stemList = self.load_json(coilId)
                image2D, imageMask, rec, steelRec = self.load2_d(coilId, stemList)
                data3D = self.load3_d(coilId, rec, stemList, jsonDatas)
                data["json"] = jsonDatas
                data["2D"] = image2D
                data["rec"] = steelRec
                data["MASK"] = imageMask

                data3D = cv2.bitwise_and(data3D, data3D, mask=imageMask)
                if Globs.control.leveling_3d and Globs.control.leveling_type == LevelingType.WK_TYPE:
                    data3D = auto_data_leveling_3d(data3D, imageMask)
                data["3D"] = data3D

                self.mk_link(coilId)
                if self.saveMask:
                    Image.fromarray(image2D).save(self.saveMaskFolder / f"{coilId}_{self.folderName}_GRAY.png")
                    Image.fromarray(imageMask).save(self.saveMaskFolder / f"{coilId}_{self.folderName}_MASK.png")

                # 显示图像
            except Exception as e:
                logger.error(f"Error in DataFolder {coilId}: {e}")
                if isLoc:
                    raise e
            finally:
                logger.info(f"DataFolder {coilId} end")
                self.consumer.put(data)
