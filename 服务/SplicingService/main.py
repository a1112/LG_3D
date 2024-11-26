import datetime
import json
import time
import traceback

from queue import Queue

import logging

from CONFIG import isLoc, serverConfigProperty
from Init import ErrorMap
from .ImageMosaic import ImageMosaic
from threading import Thread
from CoilDataBase import Coil
from CoilDataBase import tool as CoilDataBaseTool
from utils.Log import logger


class ImageMosaicThread(Thread):
    def __init__(self,managerQueue):
        super().__init__()
        self.managerQueue = managerQueue
        self.listData = []
        self.saveDataBase = True
        self.debugType = False
        self.imageMosaicList = []
        # 重新识别的排队机制
        self.reDetectionSet=set()
        self.reDetectionMsg=Queue()

        for surface in serverConfigProperty.surface:
            self.imageMosaicList.append(ImageMosaic(json.dumps(surface),self.managerQueue))
        try:
            self.startCoilId = Coil.getCoil(1)[0].SecondaryCoilId   # 最新的 数据
            self.endCoilId = Coil.getSecondaryCoil(1)[0].Id         # 目标数据
        except IndexError:
            self.startCoilId = 0

    def checkDetectionEnd(self,secondaryCoilId):
        for imageMosaic in self.imageMosaicList:
            if not imageMosaic.checkDetectionEnd(secondaryCoilId):
                logger.error("checkDetectionEnd ")
                return False
        return True

    def run(self):
        while True:
            logger.debug(f"开始处理 ")
            try:
                maxSecondaryCoilId = Coil.getSecondaryCoil(1)[0].Id
                listData = Coil.getSecondaryCoilById(self.startCoilId).all()
                # try:
                #     lastCoilSecondaryCoilId=Coil.getCoil(1)[0].SecondaryCoilId
                # except :
                #     lastCoilSecondaryCoilId = 0
                for secondaryCoilIndex in range(len(listData)):
                    secondaryCoil = listData[secondaryCoilIndex]
                    logger.debug(f"开始处理 {secondaryCoil.Id}剩余 {maxSecondaryCoilId - secondaryCoil.Id} 个")
                    if maxSecondaryCoilId - secondaryCoil.Id>2:
                        logger.debug("清理数据"+str(secondaryCoil.Id))
                        CoilDataBaseTool.clearByCoilId(secondaryCoil.Id)
                    if secondaryCoilIndex >= len(listData)-2:
                        if not self.checkDetectionEnd(secondaryCoil.Id):
                            break
                    self.startCoilId = secondaryCoil.Id
                    status = {}
                    for imageMosaic in self.imageMosaicList:  # 设置 ID
                        setOk = imageMosaic.setCoilId(secondaryCoil.Id)
                        imageMosaic.currentSecondaryCoil=secondaryCoil
                        status[imageMosaic.key] = 0
                        if not setOk:
                            logger.error(f"setOK: {setOk}")
                            status[imageMosaic.key] = ErrorMap["DataFolderError"]
                            continue
                    for imageMosaic in self.imageMosaicList:    # 获取图片
                        if status[imageMosaic.key] < 0:
                            continue
                        image = imageMosaic.getJoinImage()
                        if image is None:
                            logger.error(f"image is None {secondaryCoil.Id}")
                            status[imageMosaic.key] = ErrorMap["ImageError"]
                            continue

                    if self.saveDataBase:
                        print("saveDataBase")
                        Coil.addCoil({
                            "SecondaryCoilId": secondaryCoil.Id,
                            "DefectCountS": 0,
                            "DefectCountL": 0,
                            "CheckStatus": 0,
                            "Status_L": status["L"],
                            "Status_S": status["S"],
                            "Grade": 0,
                            "Msg": ""
                        })
                    if isLoc:
                        time.sleep(10)
                    # if self.debugType:
                    #     if self.endCoilId <= secondaryCoil.Id:
                    #         return -1
            except BaseException as e:
                error_message = traceback.format_exc()
                logger.error(error_message)
                if isLoc:
                    raise e
                return -1
            time.sleep(1)

    def addMsg(self,msg,level=logging.DEBUG):
        self.reDetectionSet.add( {
            "Base":"ImageMosaicThread",
            "time":datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "msg":msg,
            "level":logging.getLevelName(level),
        })

    def setReDetectionByCoilId(self,startId,endId):
        coilList = Coil.searchByCoilId(startId,endId)
        for coil in coilList:
            self.setReDetection(coil)
        self.addMsg("")

    def setReDetection(self,coilId):
        # 设置 重新检测 列表
        self.reDetectionSet.add(coilId.Id)

    def getReDetectionMsg(self):
        pass
