import multiprocessing
import threading
from queue import Empty, Full, Queue

from utils.MultiprocessColorLogger import logger


class _WorkBase_:
    def __init__(self, config):
        self.config = config
        self.queue_in = Queue(maxsize=10)
        self.queue_out = Queue(maxsize=10)
        self._run_ = True
        self.coil_id = None

    @property
    def __run__(self):
        return self.config.is_run()

    def add_work(self, coil_id, timeout: float = 5.0) -> bool:
        self.coil_id = coil_id
        try:
            self.queue_in.put(coil_id, timeout=timeout)
            return True
        except Full:
            logger.warning("2D work queue full: worker=%s coil_id=%s", self.__class__.__name__, coil_id)
            return False

    def get(self, timeout: float | None = None):
        try:
            return self.queue_out.get(timeout=timeout)
        except Empty:
            logger.warning("2D work output timeout: worker=%s coil_id=%s", self.__class__.__name__, self.coil_id)
            return None

    def set(self, data, timeout: float = 5.0) -> bool:
        try:
            self.queue_out.put(data, timeout=timeout)
            return True
        except Full:
            logger.warning("2D work output queue full: worker=%s coil_id=%s", self.__class__.__name__, self.coil_id)
            return False


class WorkBaseThread(_WorkBase_, threading.Thread):
    def __init__(self, config):
        threading.Thread.__init__(self, daemon=True)
        _WorkBase_.__init__(self, config)


class WorkBaseMultiProcess(_WorkBase_, multiprocessing.Process):
    def __init__(self, config):
        _WorkBase_.__init__(self, config)
        multiprocessing.Process.__init__(self)
