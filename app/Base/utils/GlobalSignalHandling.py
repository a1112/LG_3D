import logging
import os
import subprocess
from threading import Thread
from multiprocessing import current_process

logger = logging.getLogger(__name__)
DEFAULT_GLOBAL_COMMAND_TIMEOUT = 30.0


def _get_global_command_timeout() -> float:
    raw_value = os.getenv("LG3D_GLOBAL_COMMAND_TIMEOUT", str(DEFAULT_GLOBAL_COMMAND_TIMEOUT))
    try:
        return max(float(raw_value), 0.1)
    except ValueError:
        logger.warning("invalid LG3D_GLOBAL_COMMAND_TIMEOUT=%s, use %s", raw_value, DEFAULT_GLOBAL_COMMAND_TIMEOUT)
        return DEFAULT_GLOBAL_COMMAND_TIMEOUT


class GlobalSignalHandling(Thread):
    """
    在主进程处理的程序
    """
    def __init__(self, managerQueue):
        Thread.__init__(self)
        self.managerQueue = managerQueue
        process = current_process()
        self.process_name = process.name
        self.pid = process.pid
        self.command_timeout = _get_global_command_timeout()
        # if process.name == "MainProcess":


    def run(self):
        while True:
            msg_code, msgType, msgData = self.managerQueue.get()
            if msg_code in {"shutdown", "stop"}:
                logger.info("GlobalSignalHandling shutdown signal received")
                break
            if msg_code == "cmd":
                cmd, work_path = msgType, msgData
                logger.info("GlobalSignalHandling command start: %s cwd=%s", cmd, work_path)
                try:
                    result = subprocess.run(cmd, shell=True, cwd=work_path, timeout=self.command_timeout)
                    logger.info("GlobalSignalHandling command end: returncode=%s", result.returncode)
                except subprocess.TimeoutExpired:
                    logger.error("GlobalSignalHandling command timed out after %ss: %s", self.command_timeout, cmd)
                except Exception as e:
                    logger.exception("GlobalSignalHandling command failed: %s error=%s", cmd, e)
