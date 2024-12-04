import multiprocessing

import uvicorn

import Globs
from utils.GlobalSignalHandling import GlobalSignalHandling
from CONFIG import serverApiPort, isLoc

# from api import ApiDataBase,app,ApiImageServer, ApiDataServer


if isLoc:
    from CoilDataBase.Coil import deleteCoil
    deleteCoil(23000)


if __name__ == '__main__':
    multiprocessing.freeze_support()
    manager = multiprocessing.Manager()
    managerQueue = manager.Queue()
    # managerQueue = Queue()
    from SplicingService.ImageMosaicThread import ImageMosaicThread
    imageMosaicThread = ImageMosaicThread(managerQueue)  # 主进程
    imageMosaicThread.start()
    GlobalSignalHandling(managerQueue).start()
    from api import app

    Globs.imageMosaicThread=imageMosaicThread
    uvicorn.run(app, host="0.0.0.0", port=serverApiPort)
