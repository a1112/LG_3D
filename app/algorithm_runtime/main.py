"""
Standalone entry point for algorithm runtime (Lis, ZipServer, ImageMosaic).
"""
from __future__ import annotations

import faulthandler
import logging
import multiprocessing
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

faulthandler.enable(all_threads=True)

sys.path.append(str(Path(__file__).parent.parent))
sys.path.append(str(Path(__file__).parent.parent/"Base"))

from Base.utils.StdoutLog import Logger
from Base.utils.LoggerProcess import LoggerProcess
from SplicingService.ImageMosaicThread import ImageMosaicThread
from Base.utils.Singleton import SingletonLock
import Globs
from CoilDataBase.Coil import deleteCoilByCoilId
# deleteCoilByCoilId(1296711)


def _read_pid(pid_file: Path) -> int | None:
    try:
        content = pid_file.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return int(content) if content.isdigit() else None


def _terminate_process_tree(pid: int) -> bool:
    if pid <= 0 or pid == os.getpid():
        return False

    if sys.platform == "win32":
        result = subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(pid)],
            capture_output=True,
            text=True,
            timeout=20,
        )
        if result.returncode != 0:
            logging.error("Failed to terminate old 3D runtime PID %s.", pid)
            if result.stdout:
                logging.error(result.stdout.strip())
            if result.stderr:
                logging.error(result.stderr.strip())
            return False
        return True

    try:
        os.kill(pid, signal.SIGTERM)
        return True
    except OSError as e:
        logging.error("Failed to terminate old 3D runtime PID %s: %s", pid, e)
        return False


def _acquire_runtime_lock() -> SingletonLock:
    lock = SingletonLock("algorithm_runtime_3d")
    if lock.acquire():
        return lock

    old_pid = _read_pid(lock.pid_file)
    if old_pid is not None:
        logging.info("3D Algorithm Runtime is already running, restarting old PID %s...", old_pid)
        if _terminate_process_tree(old_pid):
            try:
                lock.pid_file.unlink(missing_ok=True)
            except OSError:
                pass
            time.sleep(2)

            lock = SingletonLock("algorithm_runtime_3d")
            if lock.acquire():
                logging.info("Old 3D Algorithm Runtime stopped; startup will continue.")
                return lock

    logging.error("3D Algorithm Runtime is already running.")
    logging.error("Lock file: %s", lock.pid_file)
    logging.error("Could not stop the old runtime automatically. Stop it manually and try again.")
    sys.exit(1)


def main() -> None:
    # 防重复启动检查
    lock = _acquire_runtime_lock()

    try:
        _run_main()
    finally:
        lock.release()


def _run_main() -> None:
    logging.getLogger("matplotlib").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    try:
        from ultralytics.utils import LOGGER as ULTRA_LOGGER
        ULTRA_LOGGER.setLevel(logging.WARNING)
    except Exception as e:
        logging.debug("failed to adjust ultralytics logger level: %s", e)
    Logger("算法")
    logger_process = LoggerProcess(log_file="log/app.log")
    logger_process.start()

    queue = multiprocessing.Queue(maxsize=100)

    image_mosaic_thread = ImageMosaicThread(queue, logger_process)
    image_mosaic_thread.start()
    Globs.imageMosaicThread = image_mosaic_thread

    zip_server = None
    if os.getenv("LG3D_ENABLE_LEGACY_COMPRESSION", "0") == "1":
        from SubServer.ZipServer import ZipServer
        zip_server = ZipServer(queue)
    else:
        logging.info("Legacy bmp/npy compression disabled; capture already writes jpg/npz.")
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
            except Exception as e:
                logging.exception("failed to stop image mosaic thread: %s", e)
        if zip_server is not None and zip_server.is_alive():
            zip_server.terminate()
            zip_server.join(timeout=5)
        logger_process.stop()


if __name__ == "__main__":
    main()
