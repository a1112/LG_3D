from typing import Dict

import cv2
import numpy as np

from configs.CONFIG import DEBUG
from configs.SurfaceConfig import SurfaceConfig
from utils.MultiprocessColorLogger import logger

from property.CameraImageGrop import CameraImageGrop
from .WorkBase import WorkBaseThread
from .CameraWork import CameraWork
from .SaverWork import SaverWork
from .cv_count_tool import im_show


class SurfaceWork(WorkBaseThread):
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

    def get_intersections(self,camera_image_grop_dict):

        left_index = min([item.left_index for item in camera_image_grop_dict])
        right_index = max([item.right_index for item in camera_image_grop_dict])

        intersections = camera_image_grop_dict[1].intersections

        for i in range(camera_image_grop_dict[0].left_index,camera_image_grop_dict[0].right_index):
            try:
                intersections[i] = camera_image_grop_dict[0].intersections[i]
            except:
                try:
                    intersections.append(camera_image_grop_dict[0].intersections[i])
                except IndexError:
                    pass
        return intersections,left_index,right_index

        # for item in camera_image_grop_dict:
        #     print(fr" item = {item}")
        #     print(item.intersections)
        #     print(item.left_index)
        #     print(item.right_index)
        #     print(len(item.mask_list))


    def join_images(self, camera_image_grop_dict:Dict[str,CameraImageGrop]):
        camera_image_grop_list = [camera_image_grop_dict["U"], camera_image_grop_dict["M"], camera_image_grop_dict["D"]]

        intersections,left_index,right_index = self.get_intersections(camera_image_grop_list)
        camera_image_grop_dict["U"].left_index=left_index
        camera_image_grop_dict["U"].right_index=right_index
        camera_image_grop_dict["U"].intersections=intersections


        camera_image_grop_dict["M"].set_intersections(camera_image_grop_dict["U"])
        camera_image_grop_dict["D"].set_intersections(camera_image_grop_dict["U"])

        camera_image_grop_dict["U"].init_image()
        camera_image_grop_dict["M"].init_image()
        camera_image_grop_dict["D"].init_image()



        return self._join_images_([camera_image_grop.join_image() for camera_image_grop in camera_image_grop_list])

    def _join_images_(self,image_list):
        """
        拼接图像
        """
        #  image_list = [image_dict["U"],image_dict["M"],image_dict["D"]]
        max_width = max([img.shape[1] for img in image_list if img is not None]+[0])
        if max_width<=0:
            return None
        new_image_list = []
        for img in image_list:
            # 调整图像宽度
            if img is None:
                img = np.array(np.zeros((self.config.image_size,max_width,3), np.uint8))
            if img.shape[1] < max_width:
                padding = max_width - img.shape[1]
                img = cv2.copyMakeBorder(img, 0, 0, 0, padding, cv2.BORDER_CONSTANT, value=(255, 255, 255))
            elif img.shape[1] > max_width:
                img = img[:, :max_width]
            new_image_list.append(img)
        # 纵向拼接
        result = np.vstack(new_image_list)
        # cv2.imwrite("s.jpg", result)
        if DEBUG:
            im_show(result,title=fr"max_image{self.key}")
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
                image_dict[camera_wolk.config.key[6]] = camera_wolk.get()
            try:
                max_image = self.join_images(image_dict)
                if max_image is not None:
                    self.save_wolk.add_work([coil_id, max_image])
            except AttributeError as e:
                logger.error(f"AttributeError: {e} - {self.key} - {coil_id}")
            except BaseException as e:
                logger.error(e)
                if DEBUG:
                    raise e
            self.set(None)