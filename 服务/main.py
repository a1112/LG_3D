import multiprocessing

multiprocessing.freeze_support()

from utils.GlobalSignalHandling import GlobalSignalHandling
import utils.Log

import requests
from fastapi import FastAPI
# from api import ApiDataBase,app,ApiImageServer, ApiDataServer

from CONFIG import isLoc, serverApiPort

# if isLoc:
#     from CoilDataBase.Coil import deleteCoil
#     deleteCoil(23000)


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
    uvicorn.run(app, host="0.0.0.0", port=serverApiPort)
