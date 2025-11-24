"""
Standalone entry point for algorithm runtime (Lis, ZipServer, ImageMosaic).
"""
import faulthandler, sys
from pathlib import Path

faulthandler.enable(all_threads=True)

import sys

sys.path.append(str(Path(__file__).parent.parent))
sys.path.append(str(Path(__file__).parent.parent/"Base"))

import multiprocessing
import time
import logging

from Base.utils.StdoutLog import Logger
from Base.utils.LoggerProcess import LoggerProcess
from SplicingService.ImageMosaicThread import ImageMosaicThread
from SubServer.ZipServer import ZipServer
import Globs
# from CoilDataBase.Coil import deleteCoilByCoilId
# deleteCoilByCoilId(125640)
def main() -> None:
    logging.getLogger("matplotlib").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    try:
        from ultralytics.utils import LOGGER as ULTRA_LOGGER
        ULTRA_LOGGER.setLevel(logging.WARNING)
    except Exception:
        pass
    Logger("算法")
    logger_process = LoggerProcess(log_file="log/app.log")
    logger_process.start()

    queue = multiprocessing.Queue()

    image_mosaic_thread = ImageMosaicThread(queue, logger_process)
    image_mosaic_thread.start()
    Globs.imageMosaicThread = image_mosaic_thread

    zip_server = ZipServer(queue)
    import Lis  # noqa: F401
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        if image_mosaic_thread.is_alive():
            try:
                image_mosaic_thread.stop()
                image_mosaic_thread.join(timeout=5)
            except Exception:
                pass
        if zip_server.is_alive():
            zip_server.terminate()
            zip_server.join(timeout=5)
        logger_process.stop()


if __name__ == "__main__":
    main()
