import asyncio
import json

from pathlib import Path
import time

import cv2
import numpy as np
from PIL import Image
from Base.CONFIG import isLoc, serverConfigProperty
from SplicingService.DataFolderLog import DataFolderLog
from Base.tools.Glob import cmdThread

from Base.tools import tool
from Base.tools.data3dTool import auto_data_leveling_3d

from Base.utils import Log
from Base import Globs
from Base.property.Types import LevelingType

logger = Log.logger


class DataFolder(Globs.control.BaseDataFolder):
    def __init__(self, fd, logger_process):
        super().__init__()
        self.coilAreaModel = None
        self.loggerProcess = logger_process
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
    def static_check_detection_end(source, coil_id):
        source = source / str(coil_id) / "2D"
        if not source.exists():
            return False
        bmp_list = list(source.glob("*.bmp"))
        if len(list(bmp_list)) < 3.2:   # 判断采集结束
            return False
        for bmp in bmp_list:
            file_time = bmp.stat().st_mtime
            if time.time() - file_time < 3.2:
                return False
        return True

    def get_data(self):
        return self.consumer.get()

    def set_coil_id(self, coil_id):
        self.producer.put(coil_id)

    def mk_link(self, coil_id):
        link_folder = self.saveFolder / coil_id / "link"
        link_folder.mkdir(parents=True, exist_ok=True)
        target = self.source / coil_id
        if (link_folder / self.folderName).exists():
            return
        # os.link(link_folder / self.folderName, self.source / coilId)
        cmd = fr"mklink /D {link_folder / self.folderName} {target}"
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
        max_val = max(timestamp_list_differ)
        if max_val > 200:
            max_index = timestamp_list_differ.index(max_val)
            if max_index < len(timestamp_list_differ) - 5:
                stem_list = stem_list[max_index + 1:]
                json_datas = json_datas[max_index + 1:]
        return json_datas, stem_list

    async def load2_d(self, coil_id, stem_list):
        source2_d = self.source / coil_id / "2D"

        async def read_2d(stem):
            """异步读取 BMP 文件并返回图像数据"""
            # 异步模拟读取
            image_f_ = source2_d / (stem + ".bmp")
            if not image_f_.exists():
                image_f_ = source2_d / (stem + ".jpg")
            with Image.open(image_f_) as image_:
                return np.array(image_)
        images = await asyncio.gather(*[read_2d(stem) for stem in stem_list])
        join_image = np.vstack(images)
        # images = []
        # for stem in stem_list:
        #     image_f = source2_d / (stem + ".bmp")
        #     if not image_f.exists():
        #         image_f = source2_d / (stem + ".jpg")
        #     with Image.open(image_f) as image:
        #         images.append(np.array(image))
        cv_image, mask, rec = tool.auto_crop(self.folderName, join_image, [self.cropLeft, self.cropRight], self.direction)
        steel_rec = self.coilAreaModel.getSteelRect(Image.fromarray(cv_image))
        return cv_image, mask, rec, steel_rec

    async def load3_d(self, coil_id, rec, stem_list, json_data_list):
        source3_d = self.source / coil_id / "3D"

        async def read_3d(stem):
            """异步读取 BMP 文件并返回图像数据"""
            # 异步模拟读取
            npy_f_ = source3_d / (stem + ".npy")
            if not npy_f_.exists():
                npy_f_ = source3_d / (stem + ".npz")
                return np.load(npy_f_)["array"]
            else:
                return np.load(npy_f_)


        # npy_list = []
        # for stem, jsData in zip(stem_list, json_data_list):
        #     npy_f = source3_d / (stem + ".npy")
        #     if not npy_f.exists():
        #         npz_f = source3_d / (stem + ".npz")
        #         npy = np.load(npz_f)["array"]
        #     else:
        #         npy = np.load(npy_f)
        #     npy_list.append(npy)
        # npy = np.vstack(npy_list)
        npy = np.vstack( await asyncio.gather(*[read_3d(stem) for stem in stem_list]))
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

        from Base.alg.CoilMaskModel import CoilAreaModel
        self.coilAreaModel = CoilAreaModel()
        while True:
            coil_id = self.producer.get()
            # logger.info(f"DataFolder {coil_id} start")
            data = {}
            # dataFolderLog = DataFolderLog(self)
            try:
                json_datas, stem_list = self.load_json(coil_id)
                image2_d, image_mask, rec, steel_rec = asyncio.run(self.load2_d(coil_id, stem_list))
                data3_d =  asyncio.run(self.load3_d(coil_id, rec, stem_list, json_datas))
                data["json"] = json_datas
                data["2D"] = image2_d
                data["rec"] = steel_rec
                data["MASK"] = image_mask

                data3_d = cv2.bitwise_and(data3_d, data3_d, mask=image_mask)
                if Globs.control.leveling_3d and Globs.control.leveling_type == LevelingType.WK_TYPE:
                    data3_d = auto_data_leveling_3d(data3_d, image_mask)
                data["3D"] = data3_d

                self.mk_link(coil_id)
                if self.saveMask:
                    Image.fromarray(image2_d).save(self.saveMaskFolder / f"{coil_id}_{self.folderName}_GRAY.png")
                    Image.fromarray(image_mask).save(self.saveMaskFolder / f"{coil_id}_{self.folderName}_MASK.png")

                # 显示图像
            except BaseException as e:
                logger.error(f"Error in DataFolder {coil_id}: {e}")
                if isLoc and Globs.control.debug_raise:
                    raise e
            finally:
                logger.info(f"DataFolder {coil_id} end")
                self.consumer.put(data)
