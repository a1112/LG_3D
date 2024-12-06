import json

from pathlib import Path
import time

import cv2
import numpy as np
from PIL import Image
# from multiprocessing import Process
# from multiprocessing import JoinableQueue as MulQueue
# from queue import Queue as ThreadQueue

from CONFIG import serverConfigProperty, isLoc
from SplicingService.DataFolderLog import DataFolderLog
from tools.Glob import cmdThread

from tools import tool
from tools.data3dTool import auto_data_leveling_3d

from utils import Log
import Globs

logger = Log.logger


class DataFolder(Globs.control.BaseDataFolder):
    def __init__(self, fd):
        super().__init__()
        self.coilAreaModel = None
        self.saveMaskFolder = None
        self.saveMask = None
        self.imageMosaicList = None
        fd = json.loads(fd)
        folderConfig, saveFolder, direction = fd
        self.direction = direction  # "L"
        self.saveFolder = Path(saveFolder)
        self.folderConfig = folderConfig
        self.source = Path(folderConfig["source"])
        self.folderName = self.source.stem
        self.cropLeft = folderConfig["cropLeft"]
        self.cropRight = folderConfig["cropRight"]

        self.start()

    def checkDetectionEnd(self, coilId):
        return self.staticCheckDetectionEnd(self.source, coilId)

    @staticmethod
    def staticCheckDetectionEnd(source, coilId):
        source = source / str(coilId) / "2D"
        if not source.exists():
            return False
        bmpList = list(source.glob("*.bmp"))
        if len(list(bmpList)) < 5:
            return False
        for bmp in bmpList:
            fileTime = bmp.stat().st_mtime
            if time.time() - fileTime < 5:
                return False
        return True

    def getData(self):
        return self.consumer.get()

    def setCoilId(self, coilId):
        self.producer.put(coilId)

    def mkLink(self, coilId):
        linkFolder = self.saveFolder / coilId / "link"
        linkFolder.mkdir(parents=True, exist_ok=True)
        # os.link(linkFolder / self.folderName, self.source / coilId)
        cmd = fr"mklink /D {linkFolder / self.folderName} {self.source / coilId}"
        cmdThread.put(cmd)

    def loadJson(self, coilId):
        sourceJson = self.source / coilId / "json"
        sourceJsonList = list(sourceJson.glob("*.json"))
        sourceJsonList.sort(key=lambda x: int(x.stem))
        jsonDatas = []
        for i in range(len(sourceJsonList)):
            with open(sourceJsonList[i], 'r') as f:
                jsonDatas.append(json.load(f))
        stemList = [data.stem for data in sourceJsonList]
        timestampList = [data["timestamp"] // 10e7 for data in jsonDatas]
        timestampList_differ = []
        for i in range(len(timestampList) - 1):
            timestampList_differ.append(timestampList[i + 1] - timestampList[i])
        maxVal = max(timestampList_differ)
        if maxVal > 200:
            maxIndex = timestampList_differ.index(maxVal)
            if maxIndex < len(timestampList_differ) - 5:
                stemList = stemList[maxIndex + 1:]
                jsonDatas = jsonDatas[maxIndex + 1:]
        return jsonDatas, stemList

    def load2D(self, coilId, stemList):
        source2D = self.source / coilId / "2D"
        images = []
        for stem in stemList:
            imageF = source2D / (stem + ".bmp")
            if not imageF.exists():
                imageF = source2D / (stem + ".jpg")
            with Image.open(imageF) as image:
                images.append(np.array(image))
        joinImage = np.vstack(images)
        cv_image, mask, rec = tool.autoCrop(self.folderName, joinImage, [self.cropLeft, self.cropRight], self.direction)
        steelRec = self.coilAreaModel.getSteelRect(Image.fromarray(cv_image))
        return cv_image, mask, rec, steelRec

    def load3D(self, coilId, rec, stemList, jsonDataList):
        source3D = self.source / coilId / "3D"
        npyList = []
        for stem, jsData in zip(stemList, jsonDataList):
            npyF = source3D / (stem + ".npy")
            if not npyF.exists():
                npzF = source3D / (stem + ".npz")
                npy = np.load(npzF)["array"]
            else:
                npy = np.load(npyF)
            npyList.append(npy)
        npy = np.vstack(npyList)
        if rec:
            npy = npy[:, rec[0]:rec[0] + rec[2]]
        return npy

    def hasData(self, coilId):
        return self.staticHasData(self.source, coilId)

    @staticmethod
    def staticHasData(source, coilId):
        source = Path(source)
        exists = (source / coilId).exists()
        if not exists:
            logger.error(f"DataFolder {coilId} does not exist.  {source / coilId}")
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
            dataFolderLog = DataFolderLog(self)
            try:
                jsonDatas, stemList = self.loadJson(coilId)
                image2D, imageMask, rec, steelRec = self.load2D(coilId, stemList)
                data3D = self.load3D(coilId, rec, stemList, jsonDatas)
                data["json"] = jsonDatas
                data["2D"] = image2D
                data["rec"] = steelRec
                data["MASK"] = imageMask

                data3D = cv2.bitwise_and(data3D, data3D, mask=imageMask)
                data3D = auto_data_leveling_3d(data3D, imageMask)
                data["3D"] = data3D

                self.mkLink(coilId)
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
