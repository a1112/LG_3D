import os
from queue import Queue
from threading import Thread


class CmdThread(Thread):
    def __init__(self):
        super().__init__()
        self.queue = Queue()
        self.start()

    def put(self, cmd):
        self.queue.put(cmd)

    def run(self):
        while True:
            cmd = self.queue.get()
            os.system(cmd)
            self.queue.task_done()


cmdThread = CmdThread()
