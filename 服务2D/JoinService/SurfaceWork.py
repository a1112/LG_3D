import cv2
import numpy as np

from configs.SurfaceConfig import SurfaceConfig
from .WorkBase import WorkBase
from .CameraWork import CameraWork
from .SaverWork import SaverWork
from . import tool
from .cv_count_tool import im_show


class SurfaceWork(WorkBase):
    """
    单表面
    """
    def __init__(self,key,config:SurfaceConfig):
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
        # return tool.join_image(image_list,"V")
        # cv2.imwrite("u.jpg",image_list[0])
        # cv2.imwrite("m.jpg",image_list[1])
        # cv2.imwrite("d.jpg",image_list[2])
        #纵向拼接
        # 获取最大宽度
        max_width = max(img.shape[1] for img in image_list)
        new_image_list = []
        for img in image_list:
            # 调整图像宽度
            if img.shape[1] < max_width:
                padding = max_width - img.shape[1]
                img = cv2.copyMakeBorder(img, 0, 0, 0, padding, cv2.BORDER_CONSTANT, value=(255, 255, 255))
            elif img.shape[1] > max_width:
                img = img[:, :max_width]
            new_image_list.append(img)
        # 纵向拼接
        result = np.vstack(new_image_list)
        # cv2.imwrite("s.jpg", result)

        return result

    def run(self):
        print(fr" SurfaceWork run {self.key}")
        self.cameras_wolk = [CameraWork(config) for config in self.config.camera_configs]

        while self._run_:
            coil_id = self.queue_in.get()
            image_dict = {}
            for camera_wolk in self.cameras_wolk:
                camera_wolk.add_work(coil_id)
            for camera_wolk in self.cameras_wolk:
                # print("camera_wolk " ,camera_wolk.config.key)
                # print(image_dict)
                image_dict[camera_wolk.config.key[6]] = camera_wolk.get()
            try:
                max_image = self.join_images(image_dict)

                self.save_wolk.add_work([coil_id, max_image])
            except AttributeError:
                pass
            self.set(None)