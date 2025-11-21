import datetime
import time
import traceback

from queue import Queue

import logging
from typing import List

import AlarmDetection
import AlarmDetection.detection
from Base.CONFIG import isLoc, serverConfigProperty
from Init import ErrorMap
from Base.property.Base import DataIntegrationList
from .ImageMosaic import ImageMosaic
from threading import Thread
from CoilDataBase import Coil
from CoilDataBase import tool as coil_data_base_tool
from Base.utils.Log import logger
from alg import detection as cv_detection
from Base.utils.LoggerProcess import LoggerProcess
import Globs


class ImageMosaicThread(Thread):
    """
    多线程的主循环
    """

    def __init__(self, manager_queue, logger_process: LoggerProcess):
        print("实例化 ImageMosaicThread")
        super().__init__()
        self.managerQueue = manager_queue
        self.loggerProcess = logger_process
        self.listData = []
        self.saveDataBase = True
        self.debugType = False
        self.imageMosaicList:List[ImageMosaic] = []
        # 重新识别的排队机制
        self.reDetectionSet = set() # 重新检测 set
        self.reDetectionMsg = Queue()

        for surface in serverConfigProperty.surface:
            self.imageMosaicList.append(ImageMosaic(surface, self.managerQueue, logger_process))
        try:
            self.startCoilId = Coil.get_coil(1)[0].SecondaryCoilId  # 最新的 数据
            self.endCoilId = Coil.get_secondary_coil(1)[0].Id  # 目标数据
        except IndexError:
            logger.error(" ")
            self.startCoilId = 0
    check_num=0
    def check_detection_end(self, secondary_coil_id):
        for imageMosaic in self.imageMosaicList:
            if not imageMosaic.check_detection_end(secondary_coil_id):
                self.check_num+=1
                if not (self.check_num % 10):
                    logger.error(f"checkDetectionEnd {secondary_coil_id}")
                return False
        return True

    def run(self):
        logger.debug(f"执行 算法主进程")
        while True:
            run_num = 0
            try:
                max_secondary_coil_id = Coil.get_secondary_coil(1)[0].Id
                list_data = Coil.get_secondary_coil_by_id(self.startCoilId).all()
                # list_data = list_data[-3:]
                # try:
                #     lastCoilSecondaryCoilId=Coil.getCoil(1)[0].SecondaryCoilId
                # except :
                #     lastCoilSecondaryCoilId = 0
                for secondaryCoilIndex in range(len(list_data)):
                    try:
                        defection_time1 = time.time()
                        secondary_coil = list_data[secondaryCoilIndex]
                        less_num = max_secondary_coil_id - secondary_coil.Id
                        if max_secondary_coil_id - secondary_coil.Id > 2:
                            logger.debug("清理数据" + str(secondary_coil.Id))
                            coil_data_base_tool.clear_by_coil_id(secondary_coil.Id)
                        if less_num < 1:
                            if not self.check_detection_end(secondary_coil.Id):
                                # 采集未完成
                                break
                        logger.debug(f"开始处理 {secondary_coil.Id}剩余 {less_num} 个 已处理{run_num} 个" + "-" * 100)
                        run_num += 1
                        self.startCoilId = secondary_coil.Id
                        status = {}
                        for imageMosaic in self.imageMosaicList:  # 设置 ID
                            set_ok = imageMosaic.set_coil_id(secondary_coil.Id)
                            imageMosaic.currentSecondaryCoil = secondary_coil
                            status[imageMosaic.key] = 0
                            if not set_ok:
                                logger.error(f"setOK: {set_ok}")
                                status[imageMosaic.key] = ErrorMap["DataFolderError"]
                                continue
                        data_integration_list = DataIntegrationList()
                        for imageMosaic in self.imageMosaicList:  # 获取图片
                            if status[imageMosaic.key] < 0:
                                continue
                            data_integration = imageMosaic.get_data()
                            data_integration_list.append(data_integration)  # 检测
                            if data_integration.isNone():
                                logger.error(f"image is None {secondary_coil.Id}")
                                status[imageMosaic.key] = ErrorMap["ImageError"]
                                continue

                        defection_time3 = time.time()
                        cv_detection.detection_all(data_integration_list)
                        defection_time4 = time.time()
                        AlarmDetection.detection.detection_all(data_integration_list) # 判级
                        defection_time5 = time.time()

                        logger.debug(f"完整{defection_time5 - defection_time1}= 图像处理 {defection_time3-defection_time1}"
                                     f" 缺陷 {defection_time4-defection_time3}= 3D检测 {defection_time5-defection_time4}-"
                                     f"==================================== ")
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
                            sleep_time = Globs.control.loc_sleep_time
                            if status["L"] < 0 and status["S"] < 0:
                                sleep_time = 0.1
                            logger.debug(f"loc model sleep {sleep_time}")
                            time.sleep(sleep_time)
                            logger.debug(f"loc model sleep {sleep_time} end")
                        # if self.debugType:
                        #     if self.endCoilId <= secondary_coil.Id:
                        #         return -1
                    except Exception as e:
                        logger.error(f"<UNK> {e}")
                        if isLoc:
                            raise e

            except BaseException as e:
                error_message = traceback.format_exc()
                logger.error(error_message)
                if isLoc:
                    raise e
            finally:
                import torch
                torch.cuda.empty_cache()
            time.sleep(1)

    def add_msg(self, msg, level=logging.DEBUG):
        self.reDetectionSet.add({
            "Base": "ImageMosaicThread",
            "time": datetime.datetime.now().strftime(Globs.control.exportTimeFormat),
            "msg": msg,
            "level": logging.getLevelName(level),
        })

    def set_re_detection_by_coil_id(self, startId, endId):
        coilList = Coil.searchByCoilId(startId, endId)
        for coil in coilList:
            self.set_re_detection(coil)
        self.add_msg("")

    def set_re_detection(self, coilId):
        # 设置 重新检测 列表
        self.reDetectionSet.add(coilId.Id)

    def get_re_detection_msg(self):
        return list(self.reDetectionSet)
