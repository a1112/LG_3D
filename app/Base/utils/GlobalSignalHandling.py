import logging
import subprocess
from threading import Thread
from multiprocessing import current_process

logger = logging.getLogger(__name__)


class GlobalSignalHandling(Thread):
    """
    在主进程处理的程序
    """
    def __init__(self,managerQueue):
        Thread.__init__(self)
        self.managerQueue = managerQueue
        process = current_process()
        self.process_name=process.name
        self.pid=process.pid
        # if process.name == "MainProcess":


    def run(self):
        while True:
            msg_code,msgType,msgData=self.managerQueue.get()
            if msg_code in {"shutdown", "stop"}:
                logger.info("GlobalSignalHandling shutdown signal received")
                break
            if msg_code=="cmd":
                cmd,workPath=msgType,msgData
                logger.info("GlobalSignalHandling command start: %s cwd=%s", cmd, workPath)
                result = subprocess.run(cmd, shell=True, cwd=workPath)
                logger.info("GlobalSignalHandling command end: returncode=%s", result.returncode)
