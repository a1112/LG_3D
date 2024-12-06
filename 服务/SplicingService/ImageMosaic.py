import json
import traceback
from pathlib import Path
import logging
from typing import List, Optional

import cv2
import numpy as np
import six
from PIL import Image

from Save3D.save import D3Saver

from property.ErrorBase import ServerDetectionException
from utils.DetectionSpeedRecord import DetectionSpeedRecord
from tools import tool

from CONFIG import SaveImageType, RendererList, serverConfigProperty, isLoc
from Init import ColorMaps, PreviewSize
from .DataFolder import DataFolder
from .ImageSaver import ImageSaver
from Globs import control
from property.Base import DataIntegration

from utils.Log import logger

import Globs


def getAllKey():
    return "2D","MASK","3D"


class ImageMosaic(Globs.control.BaseImageMosaic):
    def __init__(self,config,managerQueue):
        super().__init__()
        self.dataFolderList:List[DataFolder] = []
        self.d3Saver: Optional[D3Saver] = None
        self.imageSaver: Optional[ImageSaver] = None
        self.managerQueue=managerQueue
        self.currentSecondaryCoil=None
        self.colorImageDict = {}
        config=json.loads(config)
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

    def setCoilId(self, coilId):
        coilId = str(coilId)
        if not self.hasData(coilId):
            return False
        (self.saveFolder / coilId).mkdir(parents=True, exist_ok=True)
        self.producer.put(coilId)
        return True

    def _save_image_(self,dataIntegration,image,name):
        self._save_(image, dataIntegration.get_save_url("png",name + SaveImageType))
        self._save_(image, dataIntegration.get_save_url("jpg",name + ".jpg"))
        image_rgba = image.convert("RGBA")
        image_rgba.putalpha(dataIntegration.pil_mask)
        self._save_(image_rgba, dataIntegration.get_save_url("mask",name + ".png"))
        image = image.copy()
        image.thumbnail(PreviewSize)
        self._save_(image, dataIntegration.get_save_url("preview", name + ".png"))


    # 保存图像
    @DetectionSpeedRecord.timing_decorator("保存图像")
    def saveImage(self, dataIntegration:DataIntegration):
        self._save_image_(dataIntegration,dataIntegration.pil_image,"GRAY")
        self._save_image_(dataIntegration,dataIntegration.pil_mask,"MASK")

    @DetectionSpeedRecord.timing_decorator("保存json数据计时")
    def saveJson(self, dataIntegration:DataIntegration):
        coilId = dataIntegration.coilId
        data=dataIntegration.json_data
        with open(self.saveFolder / coilId / "data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)


    @DetectionSpeedRecord.timing_decorator("保存3D数据计时")
    def save3D(self,dataIntegration:DataIntegration):
        configDatas = dataIntegration.configDatas
        circleConfig = dataIntegration.circleConfig
        maskImage = dataIntegration.npy_mask
        coilId=dataIntegration.coilId

        start = dataIntegration.median_non_zero + serverConfigProperty.colorFromValue_mm // dataIntegration.scan3dCoordinateScaleZ
        self._save_(dataIntegration.npyData, self.saveFolder / coilId / "3D.npy")


        step = serverConfigProperty.colorToValue_mm // dataIntegration.scan3dCoordinateScaleZ - serverConfigProperty.colorFromValue_mm // dataIntegration.scan3dCoordinateScaleZ
        dataIntegration.set("colorFromValue_mm", serverConfigProperty.colorFromValue_mm)
        dataIntegration.set("colorToValue_mm", serverConfigProperty.colorToValue_mm)
        dataIntegration.set("start", start)
        dataIntegration.set("step", step)
        self.colorImageDict = {}
        dataIntegration.setTelescopedAlarms()
        npy__ =  dataIntegration.npyData.copy()
        non_zero_elements = npy__[npy__ != 0]
        a, b = start, start + step

        # 将图像裁剪到指定的范围 [a, b]
        depth_map_clipped = np.clip(npy__, a, b)
        # 将裁剪后的图像缩放到 [0, 255] 的范围
        depth_map_scaled = ((depth_map_clipped - a) / (b - a)) * 255
        depth_map_uint8 = depth_map_scaled.astype(np.uint8)
        mask_zero = npy__ == 0
        for name, colormap in ColorMaps.items():
            if name not in RendererList:
                continue
            depth_map_color = cv2.applyColorMap(depth_map_uint8, colormap)
            depth_map_color[mask_zero] = [0, 0, 0]  # [0, 0, 0] 表示黑色

            tool.showImage(depth_map_color) # 显示

            image = Image.fromarray(depth_map_color)
            self._save_image_(dataIntegration,image,name)
            self.colorImageDict[name] = image
        objFile = self.saveFolder / coilId / "3D.obj"
        self.d3Saver.add_([coilId, npy__, maskImage, configDatas, circleConfig, objFile,dataIntegration.median_3d_mm,dataIntegration.getBdXYZ()])

        return non_zero_elements

    def joinSaver(self):
        self.imageSaver.join()

    @DetectionSpeedRecord.timing_decorator("数据获取 __getAllData__")
    def __getAllData__(self,dataIntegration):
        # 设置 任务
        """
        对于最新的数据，应该同步完成，缺乏实时模式
        Args:
            dataIntegration:

        Returns:

        """
        for dataFolder in self.dataFolderList:
            dataFolder.setCoilId(dataIntegration.coilId)
        #  获取数据
        datas = []
        configDatas = []
        for dataFolder in self.dataFolderList:  # 获取所有的图片
            data = dataFolder.getData()
            datas.append(data)
            configDatas.append(data["json"])
        #   待修改，使用工具类型进行封装
        dataIntegration.datas, dataIntegration.configDatas = datas, configDatas

    def raiseError(self,message):
        raise ServerDetectionException(message)

    @DetectionSpeedRecord.timing_decorator("拼接图像计时")
    def __stitching__(self,dataIntegration:DataIntegration):
        minH = 0
        maxH = 0
        datas=dataIntegration.datas
        for data in datas:
            if data["rec"]:
                if data["rec"][1] < minH:
                    minH = data["rec"][1]
                if data["rec"][1] + data["rec"][3] > maxH:
                    maxH = data["rec"][1] + data["rec"][3]
        for data in datas:# 裁剪，减低计算
            for key in ["2D","MASK","3D"]:
                data[key] = data[key][minH:maxH, :]
        horizontalProjectionList = tool.getHorizontalProjectionList([data["MASK"] for data in datas])
        cross_points = tool.find_cross_points(horizontalProjectionList)
        # if dataIntegration.key=="L":
        #     input()
        print(f"cross_points {dataIntegration.coilId} {dataIntegration.key}: {cross_points}")
        #cross_points 23229: [(2096, 92), (1356, 306)]
        # cross_points 23229: [(2161, 140), (2077, 306)]
        #
        #
        dataIntegration.setCrossPoints(cross_points)

        minHeight = min([data["2D"].shape[0] for data in datas])
        for index in range(len(datas)):
            r_p = 0

            if index > 0:
                l_p = cross_points[index - 1][0]
                r_p = cross_points[index - 1][1]
                # l_p=0
                # r_p=0
                w = datas[index - 1]['2D'].shape[1]
                if l_p > serverConfigProperty.max_clip_mun:
                    l_p = w
                if self.direction == "L":
                    datas[index - 1]['2D'] = datas[index - 1]['2D'][:, :w-l_p]
                    datas[index - 1]['MASK'] = datas[index - 1]['MASK'][:, :w-l_p]
                    datas[index - 1]['3D'] = datas[index - 1]['3D'][:, :w-l_p]
            if self.direction == "R":
                datas[index]['2D'] = datas[index]['2D'][:, r_p:]
                datas[index]['MASK'] = datas[index]['MASK'][:, r_p:]
                datas[index]['3D'] = datas[index]['3D'][:, r_p:]
            datas[index]['2D'] = datas[index]['2D'][:minHeight, :]
            datas[index]['MASK'] = datas[index]['MASK'][:minHeight, :]
            datas[index]['3D'] = datas[index]['3D'][:minHeight, :]
        joinImage = np.hstack([data["2D"] for data in datas])
        joinMaskImage = np.hstack([data["MASK"] for data in datas])
        # tool.showImage(joinImage,"joinImage")
        # tool.showImage(joinMaskImage,"joinImage_mask")
        # npyData = np.hstack([data["3D"] for data in datas])

        npyData = tool.hstack3D([data["3D"] for data in datas],joinMaskImage=joinMaskImage)

        if self.rotate == 90:
            joinImage = np.rot90(joinImage,1)
            joinMaskImage = np.rot90(joinMaskImage,1)
            npyData = np.rot90(npyData,1)
        if self.rotate == -90:
            joinImage = np.rot90(joinImage, -1)
            joinMaskImage = np.rot90(joinMaskImage, -1)
            npyData = np.rot90(npyData, -1)

        joinImage = cv2.flip(joinImage, 1)
        joinMaskImage = cv2.flip(joinMaskImage, 1)
        npyData = cv2.flip(npyData, 1)


        box = tool.crop_black_border(joinMaskImage)
        x, y, w, h = box
        dataIntegration.set("rotate", self.rotate)
        dataIntegration.set("crop_box", box)
        joinMaskImage = joinMaskImage[y:y + h, x:x + w]
        joinImage = joinImage[y:y + h, x:x + w]
        npyData = npyData[y:y + h, x:x + w]
        if np.max(joinMaskImage.shape) < control.minMaskDetectErrorSize:
            self.raiseError(f"算法错误： mask shape: {joinMaskImage.shape} 小于 {control.minMaskDetectErrorSize}")
        # tool.showImage(joinMaskImage)

        circleConfig = tool.getCircleConfigByMask(joinMaskImage)
        dataIntegration.circleConfig = circleConfig
        dataIntegration.set("width", int(w))
        dataIntegration.set("height", int(h))
        dataIntegration.set("circleConfig", circleConfig)
        # if self.x_rotate:   # x、旋转
        #     npyData = tool.rotate_around_x_axis(npyData, self.x_rotate)
        #     dataIntegration.set("x_rotate", self.x_rotate)

        dataIntegration.npyData = npyData
        dataIntegration.joinImage = joinImage

        dataIntegration.npy_image=joinImage
        dataIntegration.pil_image=Image.fromarray(joinImage)

        dataIntegration.npy_mask = joinMaskImage
        dataIntegration.pil_mask = Image.fromarray(joinMaskImage)

        return joinImage, joinMaskImage, npyData

    @DetectionSpeedRecord.timing_decorator("save_all_data  全部的保存")
    def save_all_data(self,dataIntegration:DataIntegration):
        self.saveImage(dataIntegration)
        self.save3D(dataIntegration)
        self.saveJson(dataIntegration)

    def run(self):
        # 拼接后的主函数
        self.imageSaver = ImageSaver(self.managerQueue)
        self.d3Saver=D3Saver(self.managerQueue)
        self.dataFolderList =[]
        for folderConfig in self.config["folderList"]:
            fdDt=[folderConfig,self.config["saveFolder"],self.config["direction"]]
            self.dataFolderList.append(DataFolder(json.dumps(fdDt)))
        while True:
            dataIntegration = DataIntegration(self.producer.get(), self.saveFolder, self.direction, self.key)
            try:
                logger.info(f"ImageMosaic {dataIntegration.coilId}")
                self.__getAllData__(dataIntegration)  # 获取全部的拼接数据
                dataIntegration.setOriginalData(dataIntegration.datas)
                # 裁剪 2D 3D MASK
                self.__stitching__(dataIntegration)
                self.save_all_data(dataIntegration)
                dataIntegration.currentSecondaryCoil=self.currentSecondaryCoil
                # AlarmDetection.detection(dataIntegration)
                dataIntegration.commit()
            except ServerDetectionException as e:
                error_message = traceback.format_exc()
                logging.error(f"Error in ImageMosaic {dataIntegration.coilId}: {error_message}")
                dataIntegration.addServerDetectionError(e)
                print("continue Server")
            except Exception as e:
                error_message = traceback.format_exc()
                # raise e
                logging.error(f"Error in ImageMosaic {dataIntegration.coilId}: {error_message}")
                if isLoc:
                    six.reraise(Exception, e)

            finally:
                self.consumer.put(dataIntegration)

    def getData(self):
        return self.consumer.get()

    def hasFolder(self, coilId):
        """
        文件夹是否存在
        Args:
            coilId:

        Returns:

        """
        for folderConfig in self.config["folderList"]:
            if not DataFolder.staticHasData( Path(folderConfig["source"]),coilId):
                return False
        return True

    def checkDetectionEnd(self, coilId):
        for folderConfig in self.config["folderList"]:
            if not DataFolder.staticCheckDetectionEnd(Path(folderConfig["source"]),coilId):
                return False
        return True

    def hasData(self, coilId):
        return self.hasFolder(coilId)
