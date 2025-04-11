from queue import Queue
from  configs import CONFIG

class WorkBase(CONFIG.WorkClass):
    def __init__(self,config):
        super().__init__()
        self.config = config
        self.queue_in = Queue()
        self.queue_out = Queue()
        self._run_ = True

    def add_work(self, coil_id):
        self.queue_in.put(coil_id)

    def get(self):
        return self.queue_out.get()