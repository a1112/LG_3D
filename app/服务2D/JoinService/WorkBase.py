import multiprocessing
import threading
from queue import Queue
from  configs import CONFIG
from utils.MultiprocessColorLogger import logger
from collections import deque


class _WorkBase_:
    def __init__(self,config):
        super().__init__()
        self.config = config
        self.queue_in = Queue(maxsize=10)
        self.queue_out = Queue(maxsize=10)
        self._run_ = True
        self.coil_id = None

    @property
    def __run__(self):
        return self.config.is_run()

    def add_work(self, coil_id):

        self.coil_id = coil_id
        self.queue_in.put(coil_id)

    def get(self):
        data = self.queue_out.get()
        return data

    def set(self,data):
        return self.queue_out.put(data)

class WorkBaseThread(_WorkBase_,threading.Thread):
    def __init__(self,config):
        threading.Thread.__init__(self)
        _WorkBase_.__init__(self,config)

class WorkBaseMultiProcess(_WorkBase_,multiprocessing.Process):
    def __init__(self,config):
        _WorkBase_.__init__(self,config)
        multiprocessing.Process.__init__(self)