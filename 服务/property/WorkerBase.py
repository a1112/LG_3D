from abc import ABC
from multiprocessing import Process
from threading import Thread
from multiprocessing import JoinableQueue as MulQueue
from queue import Queue as ThreadQueue

class WorkerBase(ABC):
    def __init__(self, use_process=False):
        self.process = use_process
        self.queue_class = MulQueue if use_process else ThreadQueue
        self.producer = self.queue_class()
        self.consumer = self.queue_class()


class WorkerThreadBase(WorkerBase, Thread):
    def __init__(self):
        WorkerBase.__init__(self, use_process=False)
        Thread.__init__(self)


class WorkerProcessBase(WorkerBase, Process):
    def __init__(self):
        WorkerBase.__init__(self, use_process=True)
        Process.__init__(self)
