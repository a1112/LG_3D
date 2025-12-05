import datetime
import time
import traceback

import logging
from queue import Queue
from typing import List, Tuple

import AlarmDetection
import AlarmDetection.detection
from Base.CONFIG import isLoc, serverConfigProperty
from Init import ErrorMap
from Base.property.Base import DataIntegrationList
from Base.utils.Log import logger
from Base.utils.LoggerProcess import LoggerProcess
from CoilDataBase import Coil
from CoilDataBase import tool as coil_data_base_tool
from CoilDataBase.Alarm import Session as CoilSession
from CoilDataBase.models.Coil import Coil as CoilModel
from CoilDataBase.models.SecondaryCoil import SecondaryCoil as SecondaryCoilModel
from alg import detection as cv_detection
from threading import Thread
from .ImageMosaic import ImageMosaic
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

    def _process_secondary_coil(
        self,
        secondary_coil: SecondaryCoilModel,
        max_secondary_coil_id: int,
        run_num: int,
        check_detection: bool = True,
    ) -> Tuple[bool, int]:
        """
        处理单个二级卷的完整检测流程。
        """
        defection_time1 = time.time()
        less_num = max_secondary_coil_id - secondary_coil.Id
        if max_secondary_coil_id - secondary_coil.Id > 2:
            logger.debug("清理数据" + str(secondary_coil.Id))
            coil_data_base_tool.clear_by_coil_id(secondary_coil.Id)
        if check_detection and less_num < 1:
            if not self.check_detection_end(secondary_coil.Id):
                # 采集未完成
                return False, run_num

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
                "Status_L": status.get("L", 0),
                "Status_S": status.get("S", 0),
                "Grade": 0,
                "Msg": ""
            })
        if isLoc:
            sleep_time = Globs.control.loc_sleep_time
            if status.get("L", 0) < 0 and status.get("S", 0) < 0:
                sleep_time = 0.1
            logger.debug(f"loc model sleep {sleep_time}")
            time.sleep(sleep_time)
            logger.debug(f"loc model sleep {sleep_time} end")

        return True, run_num

    def run(self):
        logger.debug(f"执行 算法主进程")
        while True:
            run_num = 0
            try:
                max_secondary_coil_id = Coil.get_secondary_coil(1)[0].Id
                list_data = Coil.get_secondary_coil_by_id(self.startCoilId).all()
                if len(list_data) >1000:
                    list_data=list_data[-1000:]
                # list_data = list_data[-3:]
                # try:
                #     lastCoilSecondaryCoilId=Coil.getCoil(1)[0].SecondaryCoilId
                # except :

                #     lastCoilSecondaryCoilId = 0
                for secondary_coil in list_data:
                    try:
                        should_continue, run_num = self._process_secondary_coil(
                            secondary_coil=secondary_coil,
                            max_secondary_coil_id=max_secondary_coil_id,
                            run_num=run_num,
                            check_detection=True,
                        )
                        if not should_continue:
                            break
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

    def run_missing_coils_by_diff(self, start_id: int | None = None, end_id: int | None = None) -> None:
        """
        根据 SecondaryCoil / Coil 差异重新运行缺失历史数据。

        从大到小遍历 SecondaryCoil 表，对于 Coil 中不存在对应 SecondaryCoilId 的记录，
        复用在线检测的逻辑重新执行一次检测。

        Args:
            start_id: 起始 SecondaryCoil.Id（包含），为空则从最大 Id 开始。
            end_id: 结束 SecondaryCoil.Id（包含），为空则遍历到最小 Id。
        """
        logger.debug("开始根据数据库差异重算历史数据")
        import torch

        with CoilSession() as session:
            query = session.query(SecondaryCoilModel)
            if start_id is not None:
                query = query.filter(SecondaryCoilModel.Id >= start_id)
            if end_id is not None:
                query = query.filter(SecondaryCoilModel.Id <= end_id)
            query = query.order_by(SecondaryCoilModel.Id.desc())

            last_secondary = session.query(SecondaryCoilModel).order_by(SecondaryCoilModel.Id.desc()).first()
            if not last_secondary:
                logger.warning("SecondaryCoil 表为空, 无需重算")
                return
            max_secondary_coil_id = last_secondary.Id

            run_num = 0
            for secondary_coil in query:
                exists = (
                    session.query(CoilModel)
                    .filter(CoilModel.SecondaryCoilId == secondary_coil.Id)
                    .first()
                )
                if exists:
                    continue

                logger.info(f"历史重算 SecondaryCoilId={secondary_coil.Id}")
                try:
                    should_continue, run_num = self._process_secondary_coil(
                        secondary_coil=secondary_coil,
                        max_secondary_coil_id=max_secondary_coil_id,
                        run_num=run_num,
                        check_detection=False,
                    )
                    torch.cuda.empty_cache()
                    if not should_continue:
                        # 历史模式下通常不依赖采集结束状态，这里仅预留扩展
                        break
                except Exception as e:
                    logger.error(f"历史重算 SecondaryCoilId={secondary_coil.Id} 失败: {e}")
                    if isLoc:
                        raise e

        logger.debug("历史数据重算完成")

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
