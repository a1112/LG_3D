import multiprocessing

import uvicorn

import Globs
from SubServer.ZipServer import ZipServer
from utils.GlobalSignalHandling import GlobalSignalHandling
from CONFIG import server_api_port, isLoc, offline_mode
from utils.LoggerProcess import LoggerProcess
from utils.StdoutLog import Logger

Logger("算法")
# from api import ApiDataBase,app,ApiImageServer, ApiDataServer

if offline_mode:
    from CoilDataBase.Coil import deleteCoil
    deleteCoil(23100)

# from CoilDataBase.Coil import deleteCoil
# deleteCoil(1700)
# if isLoc:
#     from CoilDataBase.Coil import deleteCoil
#     deleteCoil(23100)


if __name__ == '__main__':
    multiprocessing.freeze_support()
    manager = multiprocessing.Manager()
    managerQueue = manager.Queue()
    from SplicingService.ImageMosaicThread import ImageMosaicThread

    loggerProcess = LoggerProcess(log_file="logs/app.log")
    loggerProcess.start()
    imageMosaicThread = ImageMosaicThread(managerQueue, loggerProcess)  # 主进程
    imageMosaicThread.start()
    GlobalSignalHandling(managerQueue).start()
    from api import app

    Globs.imageMosaicThread = imageMosaicThread
    ZipServer(managerQueue).start()
    uvicorn.run(app, host="0.0.0.0", port=server_api_port)
