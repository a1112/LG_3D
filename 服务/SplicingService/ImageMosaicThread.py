import datetime
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

    def __init__(self, manager_queue, logger_process: LoggerProcess):
        super().__init__()
        self.managerQueue = manager_queue
        self.loggerProcess = logger_process
        self.listData = []
        self.saveDataBase = True
        self.debugType = False
        self.imageMosaicList = []
        # 重新识别的排队机制
        self.reDetectionSet = set()
        self.reDetectionMsg = Queue()

        for surface in serverConfigProperty.surface:
            self.imageMosaicList.append(ImageMosaic(surface, self.managerQueue, logger_process))
        try:
            self.startCoilId = Coil.getCoil(1)[0].SecondaryCoilId  # 最新的 数据
            self.endCoilId = Coil.getSecondaryCoil(1)[0].Id  # 目标数据
        except IndexError:
            self.startCoilId = 0

    def check_detection_end(self, secondary_coil_id):
        for imageMosaic in self.imageMosaicList:
            if not imageMosaic.checkDetectionEnd(secondary_coil_id):
                logger.error("checkDetectionEnd ")
                return False
        return True

    def run(self):
        while True:
            # logger.debug(f"执行 ")
            run_num = 0
            try:
                max_secondary_coil_id = Coil.getSecondaryCoil(1)[0].Id
                list_data = Coil.getSecondaryCoilById(self.startCoilId).all()
                # 忽略 list 以前的数据
                # list_data = list_data[-1:]

                # try:
                #     lastCoilSecondaryCoilId=Coil.getCoil(1)[0].SecondaryCoilId
                # except :
                #     lastCoilSecondaryCoilId = 0

                for secondaryCoilIndex in range(len(list_data)):
                    defection_time1 = time.time()
                    secondary_coil = list_data[secondaryCoilIndex]
                    less_num = max_secondary_coil_id - secondary_coil.Id
                    if max_secondary_coil_id - secondary_coil.Id > 2:
                        logger.debug("清理数据" + str(secondary_coil.Id))
                        CoilDataBaseTool.clearByCoilId(secondary_coil.Id)
                    if less_num < 1:
                        if not self.check_detection_end(secondary_coil.Id):
                            # 采集未完成
                            break
                    logger.debug(f"开始处理 {secondary_coil.Id}剩余 {less_num} 个 已处理{run_num} 个" + "-" * 100)
                    run_num += 1
                    self.startCoilId = secondary_coil.Id
                    status = {}
                    for imageMosaic in self.imageMosaicList:  # 设置 ID
                        setOk = imageMosaic.setCoilId(secondary_coil.Id)
                        imageMosaic.currentSecondaryCoil = secondary_coil
                        status[imageMosaic.key] = 0
                        if not setOk:
                            logger.error(f"setOK: {setOk}")
                            status[imageMosaic.key] = ErrorMap["DataFolderError"]
                            continue
                    data_integration_list = DataIntegrationList()
                    for imageMosaic in self.imageMosaicList:  # 获取图片
                        if status[imageMosaic.key] < 0:
                            continue
                        data_integration = imageMosaic.getData()
                        data_integration_list.append(data_integration)  # 检测
                        if data_integration.isNone():
                            logger.error(f"image is None {secondary_coil.Id}")
                            status[imageMosaic.key] = ErrorMap["ImageError"]
                            continue
                    defection_time2 = time.time()
                    print(f"图像检测时间 {defection_time2 - defection_time1}")
                    AlarmDetection.detection_all(data_integration_list)
                    cv_detection.detectionAll(data_integration_list)
                    defection_time3 = time.time()
                    print(f"算法检测时间 {defection_time3 - defection_time2}")
                    print(f"完整检测时间 {defection_time3 - defection_time1}==============================================")
                    if self.saveDataBase:
                        Coil.addCoil({
                            "SecondaryCoilId": secondary_coil.Id,
                            "DefectCountS": 0,
                            "DefectCountL": 0,
                            "CheckStatus": 0,
                            "Status_L": status["L"],
                            "Status_S": status["S"],
                            "Grade": 0,
                            "Msg": ""
                        })
                    if isLoc:
                        sleep_time = 10
                        if status["L"] < 0 and status["S"] < 0:
                            sleep_time = 0.01
                        print(f"loc model sleep {sleep_time}")
                        "避免性能问题"
                        time.sleep(sleep_time)
                        print(f"loc model sleep {sleep_time} end")
                    # if self.debugType:
                    #     if self.endCoilId <= secondary_coil.Id:
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
