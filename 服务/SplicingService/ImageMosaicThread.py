import datetime
import json
import time
import traceback

from queue import Queue

import logging

import AlarmDetection
from CONFIG import isLoc
from Globs import serverConfigProperty
from Init import ErrorMap
from property.Base import DataIntegrationList
from .ImageMosaic import ImageMosaic
from threading import Thread
from CoilDataBase import Coil
from CoilDataBase import tool as CoilDataBaseTool
from utils.Log import logger
from alg import detection as cv_detection
from utils.LoggerProcess import LoggerProcess
import Globs


class ImageMosaicThread(Thread):
    """
    多线程的主循环
    """

    def __init__(self, managerQueue, loggerProcess: LoggerProcess):
        super().__init__()
        self.managerQueue = managerQueue
        self.loggerProcess = loggerProcess
        self.listData = []
        self.saveDataBase = True
        self.debugType = False
        self.imageMosaicList = []
        # 重新识别的排队机制
        self.reDetectionSet = set()
        self.reDetectionMsg = Queue()

        for surface in serverConfigProperty.surface:
            self.imageMosaicList.append(ImageMosaic(surface, self.managerQueue, loggerProcess))
        try:
            self.startCoilId = Coil.getCoil(1)[0].SecondaryCoilId  # 最新的 数据
            self.endCoilId = Coil.getSecondaryCoil(1)[0].Id  # 目标数据
        except IndexError:
            self.startCoilId = 0

    def checkDetectionEnd(self, secondaryCoilId):
        for imageMosaic in self.imageMosaicList:
            if not imageMosaic.checkDetectionEnd(secondaryCoilId):
                logger.error("checkDetectionEnd ")
                return False
        return True

    def run(self):
        while True:
            # logger.debug(f"执行 ")
            run_num = 0
            try:
                maxSecondaryCoilId = Coil.getSecondaryCoil(1)[0].Id
                listData = Coil.getSecondaryCoilById(self.startCoilId).all()
                # 忽略 list 以前的数据
                # listData = listData[-1:]

                # try:
                #     lastCoilSecondaryCoilId=Coil.getCoil(1)[0].SecondaryCoilId
                # except :
                #     lastCoilSecondaryCoilId = 0

                for secondaryCoilIndex in range(len(listData)):
                    defectionTime1 = time.time()
                    secondaryCoil = listData[secondaryCoilIndex]
                    less_num = maxSecondaryCoilId - secondaryCoil.Id
                    if maxSecondaryCoilId - secondaryCoil.Id > 2:
                        logger.debug("清理数据" + str(secondaryCoil.Id))
                        CoilDataBaseTool.clearByCoilId(secondaryCoil.Id)
                    if secondaryCoilIndex >= listData[- 1].Id-2:
                        if not self.checkDetectionEnd(secondaryCoil.Id):
                            # 采集未完成
                            break
                    logger.debug(f"开始处理 {secondaryCoil.Id}剩余 {less_num} 个 已处理{run_num} 个" + "-" * 100)
                    run_num += 1
                    self.startCoilId = secondaryCoil.Id
                    status = {}
                    for imageMosaic in self.imageMosaicList:  # 设置 ID
                        setOk = imageMosaic.setCoilId(secondaryCoil.Id)
                        imageMosaic.currentSecondaryCoil = secondaryCoil
                        status[imageMosaic.key] = 0
                        if not setOk:
                            logger.error(f"setOK: {setOk}")
                            status[imageMosaic.key] = ErrorMap["DataFolderError"]
                            continue
                    dataIntegrationList = DataIntegrationList()
                    for imageMosaic in self.imageMosaicList:  # 获取图片
                        if status[imageMosaic.key] < 0:
                            continue
                        dataIntegration = imageMosaic.getData()
                        dataIntegrationList.append(dataIntegration)  # 检测
                        if dataIntegration.isNone():
                            logger.error(f"image is None {secondaryCoil.Id}")
                            status[imageMosaic.key] = ErrorMap["ImageError"]
                            continue
                    defectionTime2 = time.time()
                    print(f"图像检测时间 {defectionTime2 - defectionTime1}")
                    # AlarmDetection.detectionAll(dataIntegrationList)
                    cv_detection.detectionAll(dataIntegrationList)

                    defectionTime3 = time.time()
                    print(f"算法检测时间 {defectionTime3 - defectionTime2}")
                    print(f"完整检测时间 {defectionTime3 - defectionTime1}")
                    if self.saveDataBase:
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
                        sleepTime = 10
                        print(f"loc model sleep {sleepTime}")
                        "避免性能问题"
                        time.sleep(sleepTime)
                        print(f"loc model sleep {sleepTime} end")
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

    def addMsg(self, msg, level=logging.DEBUG):
        self.reDetectionSet.add({
            "Base": "ImageMosaicThread",
            "time": datetime.datetime.now().strftime(Globs.control.exportTimeFormat),
            "msg": msg,
            "level": logging.getLevelName(level),
        })

    def setReDetectionByCoilId(self, startId, endId):
        coilList = Coil.searchByCoilId(startId, endId)
        for coil in coilList:
            self.setReDetection(coil)
        self.addMsg("")

    def setReDetection(self, coilId):
        # 设置 重新检测 列表
        self.reDetectionSet.add(coilId.Id)

    def getReDetectionMsg(self):
        pass
