from configs.SurfaceConfig import SurfaceConfig
from .WorkBase import WorkBase
from .CameraWork import CameraWork
class SurfaceWork(WorkBase):
    """
    单表面
    """
    def __init__(self,key,config):
        self.key = key
        super().__init__(config)
        self.config:SurfaceConfig
        self.cameras_wolk = []
        self.start()



    def run(self):
        print(fr" SurfaceWork run {self.key}")
        self.cameras_wolk = [CameraWork(config) for config in self.config.camera_configs]

        while self._run_:
            coil_id = self.queue_in.get()
            for camera_wolk in self.cameras_wolk:
                camera_wolk.add_work(coil_id)
            for camera_wolk in self.cameras_wolk:
                camera_wolk.get()