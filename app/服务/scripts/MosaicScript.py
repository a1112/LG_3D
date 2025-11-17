import multiprocessing

import Init
from SplicingService.ImageMosaicThread import ImageMosaicThread
from utils.LoggerProcess import LoggerProcess

Init.logDir = logDir = 'log/服务日志_restart'

if __name__ == '__main__':
    manager = multiprocessing.Manager()
    managerQueue = manager.Queue()
    loggerProcess = LoggerProcess(log_file=logDir + "/app_restart.log")
    imageMosaicThread = ImageMosaicThread(managerQueue, loggerProcess)
    imageMosaicThread.saveDataBase = False
    imageMosaicThread.debugType = True
    imageMosaicThread.startCoilId = int(input("请输入开始处理的卷ID："))
    imageMosaicThread.endCoilId = int(input("请输入结束处理的卷ID："))
    imageMosaicThread.start()
    imageMosaicThread.join()
