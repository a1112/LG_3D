import logging
import multiprocessing
import os
import threading
from typing import Optional

import Globs
from SplicingService.ImageMosaicThread import ImageMosaicThread
from SubServer.ZipServer import ZipServer
from utils.GlobalSignalHandling import GlobalSignalHandling
from utils.LoggerProcess import LoggerProcess

logger = logging.getLogger(__name__)


def _is_truthy(value: Optional[str]) -> bool:
    return str(value or "").strip().lower() not in {"0", "false", "no", "off"}


class BackgroundRuntime:
    """
    Coordinates long-running background services (algorithm loop, log collector,
    compression workers, global signal handler, etc.) so they can be started or
    stopped together and enabled/disabled through configuration.
    """

    def __init__(self, enable: Optional[bool] = None, log_file: str = "log/app.log"):
        if enable is None:
            enable = _is_truthy(os.getenv("ENABLE_BACKGROUND_RUNTIME", "1"))
        self.enable = enable
        self.log_file = log_file
        self._manager: Optional[multiprocessing.Manager] = None
        self.manager_queue = None
        self.logger_process: Optional[LoggerProcess] = None
        self.image_mosaic_thread: Optional[ImageMosaicThread] = None
        self.global_signal_thread: Optional[GlobalSignalHandling] = None
        self.zip_server: Optional[ZipServer] = None
        self._lock = threading.Lock()
        self._started = False

    def start(self):
        if not self.enable:
            logger.info("Background runtime disabled via configuration")
            return
        with self._lock:
            if self._started:
                return
            multiprocessing.freeze_support()
            self._manager = multiprocessing.Manager()
            self.manager_queue = self._manager.Queue()
            self.logger_process = LoggerProcess(log_file=self.log_file)
            self.logger_process.start()

            logger.info("Starting ImageMosaic thread")
            self.image_mosaic_thread = ImageMosaicThread(self.manager_queue, self.logger_process)
            self.image_mosaic_thread.daemon = True
            self.image_mosaic_thread.start()

            logger.info("Starting GlobalSignalHandling thread")
            self.global_signal_thread = GlobalSignalHandling(self.manager_queue)
            self.global_signal_thread.daemon = True
            self.global_signal_thread.start()

            logger.info("Starting ZipServer process")
            self.zip_server = ZipServer(self.manager_queue)
            self.zip_server.daemon = True
            self.zip_server.start()

            try:
                # Importing Lis launches its watchdog thread as a side effect.
                import Lis  # noqa: F401
            except Exception as exc:
                logger.warning("Failed to start Lis watchdog: %s", exc)

            Globs.imageMosaicThread = self.image_mosaic_thread
            self._started = True
            logger.info("Background runtime is up")

    def stop(self, timeout: float = 5.0):
        if not self.enable:
            return
        with self._lock:
            if not self._started:
                return
            logger.info("Stopping background runtime")

            if self.manager_queue:
                self.manager_queue.put(("shutdown", None, None))

            if self.zip_server and self.zip_server.is_alive():
                self.zip_server.terminate()
                self.zip_server.join(timeout=timeout)

            if self.global_signal_thread and self.global_signal_thread.is_alive():
                self.global_signal_thread.join(timeout=timeout)

            if self.logger_process:
                self.logger_process.stop()

            if self._manager:
                self._manager.shutdown()

            Globs.imageMosaicThread = None
            self.image_mosaic_thread = None
            self.global_signal_thread = None
            self.zip_server = None
            self.manager_queue = None
            self.logger_process = None
            self._manager = None
            self._started = False
            logger.info("Background runtime stopped")


runtime_controller = BackgroundRuntime()

__all__ = ["BackgroundRuntime", "runtime_controller"]
