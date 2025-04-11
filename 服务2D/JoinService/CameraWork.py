from queue import Queue
from pathlib import Path
from PIL import Image
from .WorkBase import WorkBase
from configs.CameraConfig import CameraConfig



class CameraWork(WorkBase):

    def __init__(self, config):
        super().__init__(config)
        self.start()
        self.config:CameraConfig

    def get_images(self,folder):
        image_url_list = list(folder.glob("*.jpg"))
        image_url_list.sort(key=lambda i: int(Path(i).stem))
        image_url_list = self.config.get_url_list(image_url_list)
        image_list = [Image.open(u) for u in image_url_list]
        return image_list

    def run(self):

        while self._run_:
            coil_id = self.queue_in.get()
            if not self.config.is_run():
                return
            folder = self.config.get_folder(coil_id)
            images = self.get_images(folder)
            max_image=self.horizontal_concat(images,scale = 0.2)
            print(max_image)
            max_image.save("test.jpg")


    def horizontal_concat(self,images,scale=1):

        for i in range(len(images)):
            w, h = images[i].size
            images[i] = images[i].crop([1200, 0, w-1200, h])
        # 打开所有图像并转换为Image对象
        imgs = [Image.open(i) if isinstance(i, str) else i for i in images]
        for i in range(len(imgs)):
            size=imgs[i].size
            imgs[i] = imgs[i].resize((int(size[0] * 0.2), int(size[1] * 0.2)))
        # 计算总宽度和最大高度
        widths, heights = zip(*(i.size for i in imgs))
        total_width = sum(widths)
        max_height = max(heights)

        # 创建新图像
        new_img = Image.new('L', (total_width, max_height))

        # 粘贴图像
        x_offset = 0
        for img in imgs:
            new_img.paste(img, (x_offset, 0))
            x_offset += img.size[0]

        return new_img