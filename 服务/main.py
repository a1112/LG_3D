import multiprocessing

import uvicorn

import Globs
from utils.GlobalSignalHandling import GlobalSignalHandling
from CONFIG import serverApiPort, isLoc
from utils.LoggerProcess import LoggerProcess

# from api import ApiDataBase,app,ApiImageServer, ApiDataServer

# from CoilDataBase.Coil import deleteCoil
# deleteCoil(34500)
# if isLoc:
#     from CoilDataBase.Coil import deleteCoil
#     deleteCoil(23006)


if __name__ == '__main__':
    multiprocessing.freeze_support()
    manager = multiprocessing.Manager()
    managerQueue = manager.Queue()
    from SplicingService.ImageMosaicThread import ImageMosaicThread

    loggerProcess = LoggerProcess(log_file="logs/app.log")
    loggerProcess.start()
    imageMosaicThread = ImageMosaicThread(managerQueue,loggerProcess)  # 主进程
    imageMosaicThread.start()
    GlobalSignalHandling(managerQueue).start()
    from api import app

    Globs.imageMosaicThread=imageMosaicThread
    uvicorn.run(app, host="0.0.0.0", port=serverApiPort)
