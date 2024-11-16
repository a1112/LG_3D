import multiprocessing
import subprocess
from threading import Thread
from multiprocessing import Manager, current_process
multiprocessing.Process

class GlobalSignalHandling(Thread):
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
            if msg_code=="cmd":
                cmd,workPath=msgType,msgData
                print("GlobalSignalHandling", msg_code, msgType, msgData)
                subprocess.run(cmd, shell=True, cwd=workPath)
                print("GlobalSignalHandling END",msg_code,msgType,msgData)
