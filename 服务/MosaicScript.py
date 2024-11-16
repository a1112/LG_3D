import multiprocessing

import CONFIG
import Init
from SplicingService.main import ImageMosaicThread
Init.logDir =logDir= 'logs/服务日志_restart'

from SplicingService import ImageMosaic,ImageSaver

if __name__ == '__main__':
    import uvicorn
    manager = multiprocessing.Manager()
    managerQueue = manager.Queue()
    imageMosaicThread = ImageMosaicThread(managerQueue)
    imageMosaicThread.saveDataBase = False
    imageMosaicThread.debugType = True
    imageMosaicThread.startCoilId = int(input("请输入开始处理的卷ID："))
    imageMosaicThread.endCoilId = int(input("请输入结束处理的卷ID："))
    imageMosaicThread.start()
    imageMosaicThread.join()
