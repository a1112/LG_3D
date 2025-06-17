from pathlib import Path
from PIL import Image

from configs.CameraConfig import CameraConfig
from configs.SurfaceConfig import SurfaceConfig
from utils.MultiprocessColorLogger import logger
from .WorkBase import WorkBaseThread

class SaverWork(WorkBaseThread):
    def __init__(self,config:SurfaceConfig):
        super().__init__(config)
        self.start()
        self.config:SurfaceConfig
        self.size=(512, 512)

    def save_thumbnail(self,url_,image):
        image.thumbnail(self.size)
        # if CONFIG.DEBUG:
        #     image.show()
        image.save(url_)

    def run(self):
        while self.__run__:
            coil_id,image = self.queue_in.get()
            image=Image.fromarray(image)
            save_f=self.config.get_area_url(coil_id)
            save_f.parent.mkdir(parents=True, exist_ok=True)

            save_t=self.config.get_area_url_pre(coil_id)
            save_t.parent.mkdir(parents=True, exist_ok=True)
            try:
                logger.debug(fr"图像保存： {save_f}")
                image.save(save_f)
                self.save_thumbnail(save_t,image)
            except BaseException as e:
                print(e)


class DebugSaveWork(WorkBaseThread):
    """
    保存用来识别模型的数据

    """
    def __init__(self,config):
        self.config:CameraConfig = config
        self.image_save_folder = Path(fr"D:\AreaSaveFolder")
        self.image_save_folder.mkdir(parents=True, exist_ok=True)
        super().__init__(config)
        self.start()

    def run(self):
        while self._run_:
            coil_id, camera_key, index, image = self.queue_in.get()
            save_f = self.image_save_folder / fr"{camera_key}_{coil_id}_{index}.jpg"
            image.thumbnail((1024, 1024))
            image.save(save_f)