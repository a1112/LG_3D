from pathlib import Path
from PIL import Image
from configs.SurfaceConfig import SurfaceConfig
from .WorkBase import WorkBase

class SaverWork(WorkBase):
    def __init__(self,config):
        super().__init__(config)
        self.start()
        self.config:SurfaceConfig
        self.size=(512, 512)

    def save_thumbnail(self,url_,image,):
        image.thumbnail(self.size)
        image.save(url_)

    def run(self):
        while self._run_:
            coil_id,image = self.queue_in.get()
            save_f=self.config.get_area_url(coil_id)
            save_f.parent.mkdir(parents=True, exist_ok=True)

            save_t=self.config.get_area_url_pre(coil_id)
            save_t.parent.mkdir(parents=True, exist_ok=True)
            try:
                image.save(save_f)
                self.save_thumbnail(save_t,image)
            except BaseException as e:
                print(e)


class DebugSaveWork(WorkBase):
    """
    保存用来识别模型的数据

    """
    def __init__(self,config):
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