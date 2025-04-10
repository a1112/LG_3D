from queue import Queue
from pathlib import Path
from PIL import Image
from .WorkBase import WorkBase
from configs.CameraConfig import CameraConfig
from .SurfaceWork import SurfaceWork


class CameraWork(WorkBase):

    def __init__(self, config):
        super().__init__(config)
        self.start()
        self.config:CameraConfig

    def get_images(self,folder):
        image_url_list = list(folder.glob("*.jpg"))
        image_url_list.sort(key=lambda i: int(Path(i).stem))
        # image_url_list = image_url_list[:][::-1]
        image_list = [Image.open(u) for u in image_url_list]
        return image_list

    def run(self):
        if not self.config.is_run():
            return
        while self._run_:
            coil_id = self.queue_in.get()
            folder = self.config.get_folder(coil_id)
            images = self.get_images(folder)
            print(images)