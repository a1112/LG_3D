from queue import Queue
from  configs import CONFIG

class WorkBase(CONFIG.WorkClass):
    def __init__(self,config):
        super().__init__()
        self.config = config
        self.queue_in = Queue()
        self.queue_out = Queue()
        self._run_ = True

    def add_work(self, data):
        self.queue_in.put(data)

    def get(self):
        return self.queue_out.get()

    def set(self,data):
        return self.queue_out.put(data)
