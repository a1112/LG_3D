from queue import Queue
from pathlib import Path
from PIL import Image

from .SaverWork import DebugSaveWork
from .WorkBase import WorkBase
from configs.CameraConfig import CameraConfig
from . import tool
from configs import CONFIG

class CameraWork(WorkBase):

    def __init__(self, config):
        super().__init__(config)
        self.scale=1
        self.start()
        self.config:CameraConfig
        self.debug_work = None
        if CONFIG.DEBUG:
            self.debug_work = DebugSaveWork(self.config)

    def get_images(self, folder,coil_id):
        image_url_list = list(folder.glob("*.jpg"))
        image_url_list.sort(key=lambda i: int(Path(i).stem))
        image_url_list = self.config.get_url_list(image_url_list)
        image_list = [Image.open(u) for u in image_url_list]

        if self.debug_work is not None:
            for url_,image_ in zip(image_url_list,image_list):
                index = Path(url_).stem
                self.debug_work.add_work([coil_id, self.config.key, index, image_.copy()])


        return image_list

    def run(self):
        self.config: CameraConfig
        while self._run_:
            coil_id = self.queue_in.get()
            if not self.config.is_run():
                return
            folder = self.config.get_folder(coil_id)
            images = self.get_images(folder,coil_id)
            try:
                max_image = self.horizontal_concat(images)
                print(max_image)
                # print(max_image)
                # max_image.save(fr"test_{self.config.key}.jpg")
                self.set(max_image)
            except ValueError as e:
                print(e)
                print(images)
                self.set(None)


    def horizontal_concat(self,images):
        for i in range(len(images)):
            w, h = images[i].size
            images[i] = images[i].crop([1100, 0, w-1100, h])
        # 打开所有图像并转换为Image对象
        imgs = [Image.open(i) if isinstance(i, str) else i for i in images]
        new_img=tool.join_image(imgs,"H", self.scale)
        return new_img