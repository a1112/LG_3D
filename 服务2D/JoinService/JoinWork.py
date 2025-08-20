from queue import Queue

from configs import CONFIG
from .WorkBase import WorkBaseThread
from configs.JoinConfig import JoinConfig
from .SurfaceWork import SurfaceWork

class JoinWork(WorkBaseThread):
    """
      对于 整体的  拼接  工作
      主要类别
    """

    def __init__(self, config:JoinConfig):

        super().__init__(config)
        self.config: JoinConfig
        self.surface_dict = {}
        self._run_ = True
        self.start()

    def run(self):
        self.surface_dict = {key: SurfaceWork(key, surface_config) for key, surface_config in
                             self.config.surfaces.items()}

        while self._run_:
            coil_id = self.queue_in.get()
            for key, surface in self.surface_dict.items():
                surface.add_work(coil_id)
            for key, surface in self.surface_dict.items():
                surface.get()
            self.set(None)