import asyncio
import json
import traceback
from pathlib import Path
import logging
from threading import Thread
from typing import List, Optional

import cv2
import numpy as np
from PIL import Image

import AlarmDetection
from Save3D.save import D3Saver

from property.ErrorBase import ServerDetectionException
from property.Types import LevelingType
from utils.DetectionSpeedRecord import DetectionSpeedRecord
from tools import tool, FlattenSurface

from CONFIG import isLoc
from Init import ColorMaps, PreviewSize
from .DataFolder import DataFolder
from .ImageSaver import ImageSaver
from Globs import control, serverConfigProperty
from property.Base import DataIntegration

from utils.Log import logger
from utils.LoggerProcess import LoggerProcess

import Globs


def getAllKey():
    return "2D", "MASK", "3D"


def leveling_2d(datas):
    if Globs.control.leveling_gray:  # 调整灰度
        media_gray_list = []
        for data in datas:
            media_gray = np.median(data["2D"][data["2D"] != 0])
            media_gray_list.append(media_gray)
        print(f"media_gray_list {media_gray_list}")
        if min(media_gray_list) < 0.5 or max(media_gray_list) > 2:
            logger.error(f"leveling_2d 失败")
            return
        datas[0]["2D"] = (datas[0]["2D"].astype(np.float32) * (media_gray_list[1] / media_gray_list[0])).astype(
            np.uint8)
        datas[2]["2D"] = (datas[2]["2D"].astype(np.float32) * (media_gray_list[1] / media_gray_list[2])).astype(
            np.uint8)


class ImageMosaic(Globs.control.BaseImageMosaic):
    def __init__(self, config, managerQueue, logger_process: LoggerProcess):
        super().__init__()
        self.dataFolderList: List[DataFolder] = []
        self.d3Saver: Optional[D3Saver] = None
        self.imageSaver: Optional[ImageSaver] = None
        self.managerQueue = managerQueue
        self.currentSecondaryCoil = None
        self.colorImageDict = {}
        self.loggerProcess = logger_process
        self.config = config
        self.key = config["key"]
        self.saveFolder = Path(config["saveFolder"])
        self.rotate = config["rotate"]
        self.direction = config["direction"]
        self.x_rotate = config["x_rotate"]
        self.save3D_data = getattr(config, "save3D_data", True)
        self.save = True
        self.saveFolder.mkdir(parents=True, exist_ok=True)
        self.dataList = []
        self.start()

    def setSave(self, save: bool):
        self.save = save

    def _save_(self, image, path):
        if self.save:
            return self.imageSaver.add(image, path)

    def set_coil_id(self, coil_id):
        coil_id = str(coil_id)
        if not self.has_data(coil_id):
            return False
        (self.saveFolder / coil_id).mkdir(parents=True, exist_ok=True)
        self.producer.put(coil_id)
        return True

    def _save_image_(self, data_integration, image, name):
        self._save_(image, data_integration.get_save_url("png", name + serverConfigProperty.save_image_type))
        self._save_(image, data_integration.get_save_url("jpg", name + ".jpg"))
        image_rgba = image.convert("RGBA")
        image_rgba.putalpha(data_integration.pil_mask)
        self._save_(image_rgba, data_integration.get_save_url("mask", name + ".png"))
        image = image.copy()
        image.thumbnail(PreviewSize)
        self._save_(image, data_integration.get_save_url("preview", name + ".png"))

    # 保存图像
    async def save_image(self, data_integration: DataIntegration):
        self._save_image_(data_integration, data_integration.pil_image, "GRAY")
        self._save_image_(data_integration, data_integration.pil_mask, "MASK")

    async def save_json(self, data_integration: DataIntegration):
        coil_id = data_integration.coilId
        data = data_integration.json_data
        with open(self.saveFolder / coil_id / "data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    async def save3_d(self, data_integration: DataIntegration):
        config_datas = data_integration.configDatas
        circle_config = data_integration.circle_config
        mask_image = data_integration.npy_mask
        coil_id = data_integration.coilId

        start = data_integration.median_non_zero + serverConfigProperty.colorFromValue_mm // data_integration.scan3dCoordinateScaleZ
        self._save_(data_integration.npy_data, self.saveFolder / coil_id / "3D.npy")

        step = (serverConfigProperty.colorToValue_mm - serverConfigProperty.colorFromValue_mm) // data_integration.scan3dCoordinateScaleZ
        data_integration.set("colorFromValue_mm", serverConfigProperty.colorFromValue_mm)
        data_integration.set("colorToValue_mm", serverConfigProperty.colorToValue_mm)
        data_integration.set("start", start)
        data_integration.set("step", step)
        self.colorImageDict = {}
        data_integration.set_telescoped_alarms()
        npy__ = data_integration.npy_data
        non_zero_elements = npy__[npy__ != 0]
        a, b = start, start + step
        depth_map_clipped = np.clip(npy__, a, b)
        depth_map_scaled = ((depth_map_clipped - a) / (b - a)) * -255 + 255
        depth_map_uint8 = depth_map_scaled.astype(np.uint8)
        mask_zero = npy__ == 0
        for name, colormap in ColorMaps.items():
            if name not in serverConfigProperty.renderer_list:
                continue
            depth_map_color = cv2.applyColorMap(depth_map_uint8, colormap)
            depth_map_color[mask_zero] = [0, 0, 0]  # [0, 0, 0] 表示黑色

            image = Image.fromarray(depth_map_color)
            self._save_image_(data_integration, image, name)
            self.colorImageDict[name] = image
        obj_file = self.saveFolder / coil_id / "3D.obj"
        self.d3Saver.add_([coil_id, npy__, mask_image, config_datas, circle_config, obj_file, data_integration.median_3d_mm,
                           data_integration.get_bd_xyz()])
        return non_zero_elements

    def join_saver(self):
        self.imageSaver.join()

    @DetectionSpeedRecord.timing_decorator("数据获取 __getAllData__")
    def __getAllData__(self, data_integration):
        # 设置 任务
        """
        对于最新的数据，应该同步完成，缺乏实时模式
        Args:
            data_integration:

        Returns:

        """
        for dataFolder in self.dataFolderList:
            dataFolder.set_coil_id(data_integration.coilId)
        #  获取数据
        datas = []
        config_datas = []
        for dataFolder in self.dataFolderList:  # 获取所有的图片
            data = dataFolder.get_data()
            datas.append(data)
            print(data["json"])
            config_datas.append(data["json"])
        #   待修改，使用工具类型进行封装
        data_integration.datas, data_integration.configDatas = datas, config_datas

    def raise_error(self, message):
        raise ServerDetectionException(message)

    @DetectionSpeedRecord.timing_decorator("拼接图像计时")
    def __stitching__(self, data_integration: DataIntegration):
        min_h = 0
        max_h = 0
        datas = data_integration.datas
        for data in datas:
            if data["rec"]:
                if data["rec"][1] < min_h:
                    min_h = data["rec"][1]
                if data["rec"][1] + data["rec"][3] > max_h:
                    max_h = data["rec"][1] + data["rec"][3]
        for data in datas:  # 裁剪，减低计算
            for key in ["2D", "MASK", "3D"]:
                data[key] = data[key][min_h:max_h, :]
        horizontal_projection_list = tool.get_horizontal_projection_list([data["MASK"] for data in datas])
        cross_points = tool.find_cross_points(horizontal_projection_list)
        print(f"cross_points {data_integration.coilId} {data_integration.key}: {cross_points}")
        data_integration.set_cross_points(cross_points)

        min_height = min([data["2D"].shape[0] for data in datas])
        for index in range(len(datas)):
            datas[index]['2D'] = datas[index]['2D'][:min_height, :]
            datas[index]['MASK'] = datas[index]['MASK'][:min_height, :]
            datas[index]['3D'] = datas[index]['3D'][:min_height, :]
            if index > 0:
                l_p = cross_points[index - 1][0]
                r_p = cross_points[index - 1][1]
                w = datas[index - 1]['2D'].shape[1]
                if l_p > serverConfigProperty.max_clip_mun:
                    l_p = 0
                if self.direction == "L":
                    datas[index - 1]['2D'] = datas[index - 1]['2D'][:, :w - l_p]
                    datas[index - 1]['MASK'] = datas[index - 1]['MASK'][:, :w - l_p]
                    datas[index - 1]['3D'] = datas[index - 1]['3D'][:, :w - l_p]

                if self.direction == "R":
                    datas[index]['2D'] = datas[index]['2D'][:, r_p:]
                    datas[index]['MASK'] = datas[index]['MASK'][:, r_p:]
                    datas[index]['3D'] = datas[index]['3D'][:, r_p:]

        leveling_2d(datas)
        join_image = np.hstack([data["2D"] for data in datas])
        join_mask_image = np.hstack([data["MASK"] for data in datas])

        if Globs.control.leveling_3d and Globs.control.leveling_type == LevelingType.WK_TYPE:
            npy_data = np.hstack([data["3D"] for data in datas])
        else:
            npy_data = tool.hstack_3d([data["3D"] for data in datas], joinMaskImage=join_mask_image)

        if self.rotate == 90 or data_integration.surface == "S":
            join_image = np.rot90(join_image, 1)
            join_mask_image = np.rot90(join_mask_image, 1)
            npy_data = np.rot90(npy_data, 1)
            join_image = cv2.flip(join_image, 1)
            join_mask_image = cv2.flip(join_mask_image, 1)
            npy_data = cv2.flip(npy_data, 1)

        if self.rotate == -90 or data_integration.surface == "L":
            join_image = np.rot90(join_image, -1)
            join_mask_image = np.rot90(join_mask_image, -1)
            npy_data = np.rot90(npy_data, -1)

        box = tool.crop_black_border(join_mask_image)
        x, y, w, h = box
        data_integration.set("rotate", self.rotate)
        data_integration.set("crop_box", box)
        join_mask_image = join_mask_image[y:y + h, x:x + w]
        join_image = join_image[y:y + h, x:x + w]
        npy_data = npy_data[y:y + h, x:x + w]
        if np.max(join_mask_image.shape) < control.minMaskDetectErrorSize:
            self.raise_error(f"算法错误： mask shape: {join_mask_image.shape} 小于 {control.minMaskDetectErrorSize}")
        data_integration.joinImage = join_image

        data_integration.npy_image = join_image
        data_integration.pil_image = Image.fromarray(join_image)

        data_integration.npy_mask = join_mask_image
        data_integration.pil_mask = Image.fromarray(join_mask_image)
        data_integration.set_npy_data(npy_data)
        if Globs.control.leveling_3d and Globs.control.leveling_type == LevelingType.LinearRegression:
            r_z = data_integration.flatten_surface_by_rotation()
            npy_data = tool.rotate_around_x_axis(npy_data, r_z)
            data_integration.set("x_rotate", r_z)
            data_integration.set_npy_data(npy_data)

        if Globs.control.leveling_3d and Globs.control.leveling_type == LevelingType.Config:
            if self.x_rotate:  # x、旋转
                npy_data = tool.rotate_around_x_axis(npy_data, self.x_rotate)
                data_integration.set("x_rotate", self.x_rotate)
                data_integration.set_npy_data(npy_data)

        return join_image, join_mask_image, npy_data

    @DetectionSpeedRecord.timing_decorator("图像保持")
    def sync_save(self,data_integration):
        return asyncio.run(self.save_all_data(data_integration))

    async def save_all_data(self, data_integration: DataIntegration):
        await self.save_image(data_integration)
        await self.save3_d(data_integration)
        await self.save_json(data_integration)

    def run(self):
        # 拼接后的主函数
        self.imageSaver = ImageSaver(self.managerQueue, self.loggerProcess)
        self.d3Saver = D3Saver(self.managerQueue, self.loggerProcess)
        self.dataFolderList = []
        for folderConfig in self.config["folderList"]:
            fd_dt = [folderConfig, self.config["saveFolder"], self.config["direction"]]
            self.dataFolderList.append(DataFolder(fd_dt, self.loggerProcess.get_logger()))
        while True:
            data_integration = DataIntegration(self.producer.get(), self.saveFolder, self.direction, self.key)
            try:
                logger.info(f"ImageMosaic {data_integration.coilId}")
                self.__getAllData__(data_integration)  # 获取全部的拼接数据
                data_integration.set_original_data(data_integration.datas)
                # 裁剪 2D 3D MASK
                self.__stitching__(data_integration)
                self.sync_save(data_integration)
                # Thread(target=self.sync_save, args=(data_integration,)).start()
                # self.sync_save(data_integration)
                data_integration.currentSecondaryCoil = self.currentSecondaryCoil
                # AlarmDetection.detection(data_integration)

                # AlarmDetection.detectionAll(data_integration)

                data_integration.commit()
            except ServerDetectionException as e:
                error_message = traceback.format_exc()
                logging.error(f"Error in ImageMosaic {data_integration.coilId}: {error_message}")
                data_integration.addServerDetectionError(e)
                print("continue Server")
            except Exception as e:
                error_message = traceback.format_exc()
                # raise e
                logging.error(f"Error in ImageMosaic {data_integration.coilId}: {error_message}")
                if isLoc and Globs.control.debug_raise:
                    import six
                    six.reraise(Exception, e)

            finally:
                self.consumer.put(data_integration)

    def get_data(self):
        return self.consumer.get()

    def has_folder(self, coil_id):
        """
        文件夹是否存在
        Args:
            coil_id:

        Returns:

        """
        for folderConfig in self.config["folderList"]:
            if not DataFolder.static_has_data(Path(folderConfig["source"]), coil_id):
                return False
        return True

    def check_detection_end(self, coil_id):
        for folderConfig in self.config["folderList"]:
            if not DataFolder.static_check_detection_end(Path(folderConfig["source"]), coil_id):
                return False
        return True

    def has_data(self, coil_id):
        return self.has_folder(coil_id)
