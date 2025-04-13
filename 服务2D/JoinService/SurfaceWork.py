from configs.SurfaceConfig import SurfaceConfig
from .WorkBase import WorkBase
from .CameraWork import CameraWork
from .SaverWork import SaverWork
from . import tool

class SurfaceWork(WorkBase):
    """
    单表面
    """
    def __init__(self,key,config):
        self.key = key
        super().__init__(config)
        self.config:SurfaceConfig
        self.save_wolk = SaverWork(self.config)
        self.cameras_wolk = []
        self.start()


    def join_images(self,image_dict):
        """
        拼接图像
        """
        image_list = [image_dict["U"],image_dict["M"],image_dict["D"]]
        return tool.join_image(image_list,"V")


    def run(self):
        print(fr" SurfaceWork run {self.key}")
        self.cameras_wolk = [CameraWork(config) for config in self.config.camera_configs]

        while self._run_:
            coil_id = self.queue_in.get()
            image_dict = {}
            for camera_wolk in self.cameras_wolk:
                camera_wolk.add_work(coil_id)
            for camera_wolk in self.cameras_wolk:
                image_dict[camera_wolk.config.key[6]] = camera_wolk.get()
            try:
                max_image = self.join_images(image_dict)
                self.save_wolk.add_work([coil_id, max_image])
            except AttributeError:
                pass
            self.set(None)