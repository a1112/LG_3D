import subprocess
from threading import Thread
from multiprocessing import current_process


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
                print("GlobalSignalHandling shutdown signal received")
                break
            if msg_code=="cmd":
                cmd,workPath=msgType,msgData
                print("GlobalSignalHandling", msg_code, msgType, msgData)
                subprocess.run(cmd, shell=True, cwd=workPath)
                print("GlobalSignalHandling END",msg_code,msgType,msgData)
