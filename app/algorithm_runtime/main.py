"""
Standalone entry point for algorithm runtime (Lis, ZipServer, ImageMosaic).
"""

import multiprocessing
import sys
import time
from pathlib import Path

# Ensure shared Base modules are on import path
BASE_DIR = Path(__file__).resolve().parents[1] / "Base"
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from Base.utils.StdoutLog import Logger
from Base.utils.LoggerProcess import LoggerProcess
from SplicingService.ImageMosaicThread import ImageMosaicThread
from SubServer.ZipServer import ZipServer
import Globs


def main() -> None:
    multiprocessing.freeze_support()
    Logger("算法")
    logger_process = LoggerProcess(log_file="log/app.log")
    logger_process.start()

    queue = multiprocessing.Queue()

    image_mosaic_thread = ImageMosaicThread(queue, logger_process)
    image_mosaic_thread.daemon = True
    image_mosaic_thread.start()
    Globs.imageMosaicThread = image_mosaic_thread

    zip_server = ZipServer(queue)
    zip_server.daemon = True
    zip_server.start()

    try:
        # 导入 Lis 会启动其内部监控线程，确保只触发一次
        import Lis  # noqa: F401
    except Exception:
        pass

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        if zip_server.is_alive():
            zip_server.terminate()
            zip_server.join(timeout=5)
        if image_mosaic_thread.is_alive():
            image_mosaic_thread.join(timeout=5)
        logger_process.stop()


if __name__ == "__main__":
    main()
