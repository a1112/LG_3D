import sys
from multiprocessing import freeze_support
from queue import Queue

freeze_support()
# if not ctypes.windll.shell32.IsUserAnAdmin():
#     ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, __file__, None, 1)
import multiprocessing

from utils.GlobalSignalHandling import GlobalSignalHandling
import utils.Log

# multiprocessing.set_start_method('spawn', force=True)

import requests
from fastapi import FastAPI
# from api import ApiDataBase,app,ApiImageServer, ApiDataServer

from CONFIG import isLoc
# if isLoc:
#     from CoilDataBase.Coil import deleteCoil
#     deleteCoil(23000)


# 捕获共享数据
# GlobalSignalHandling().start()
if __name__ == '__main__':
    manager = multiprocessing.Manager()
    managerQueue = manager.Queue()
    # managerQueue = Queue()
    from SplicingService.main import ImageMosaicThread
    import uvicorn
    imageMosaicThread = ImageMosaicThread(managerQueue)
    imageMosaicThread.start()
    GlobalSignalHandling(managerQueue).start()
    from api import app, ApiServer
    ApiServer.imageMosaicThread=imageMosaicThread
    uvicorn.run(app, host="0.0.0.0", port=6010)
