import logging

import CONFIG
from CONFIG import isLoc
from Globs import control
from Base.property.ServerConfigProperty import SurfaceConfigProperty
from Base.utils.Zip import ZipAndDeletionCameraData, ZipAndDeletionSaveData


class ZipServer(control.ProcessClass):
    """
    对服务器单数据进行压缩
    """
    def __init__(self, manager_queue):
        super().__init__()
        self.managerQueue = manager_queue

    def run(self):
        if isLoc:
            logging.info("local environment skips legacy compression")
            return
        logging.info("legacy raw data compression process started")
        zip_and_deletion_list = []
        for surface in CONFIG.serverConfigProperty.surfaceConfigPropertyDict.values():
            surface: SurfaceConfigProperty
            for folder in surface.folderList:
                zip_and_deletion_list.append(ZipAndDeletionCameraData(folder["source"], reserve_num=100))
            zip_and_deletion_list.append(ZipAndDeletionSaveData(surface.saveFolder, reserve_num=100))

        for item in zip_and_deletion_list:
            item.start()

        logging.info("legacy saved data compression process started")

        # 数据进程
        for item in zip_and_deletion_list:
            item.join()
