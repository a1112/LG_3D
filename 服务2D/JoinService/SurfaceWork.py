from typing import Dict

import cv2
import numpy as np

from alg.detection import detection
from configs.CONFIG import DEBUG
from configs.SurfaceConfig import SurfaceConfig
from utils.MultiprocessColorLogger import logger

from property.CameraImageGrop import CameraImageGrop

from property.DataIntegration import DataIntegration

from .WorkBase import WorkBaseThread
from .CameraWork import CameraWork
from .SaverWork import SaverWork
from .cv_count_tool import im_show
from alg.detection import detection
from CoilDataBase.Coil import get_coilState
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


    def join_images(self, camera_image_grop_dict:Dict[str,CameraImageGrop],coil_id):
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
        return self._join_images_([camera_image_grop.join_image() for camera_image_grop in camera_image_grop_list],coil_id)

    def get_num_clip_by_mm(self,coil_state,median_3d_mm):
        # c = a*x+b    b= -700  a=1
        if coil_state.surface=="S":
            b=530
            a=1.5
            c = (median_3d_mm-b)*a
            print(fr" coil_state {coil_state.secondaryCoilId}  {coil_state.surface} median_3d:{coil_state.median_3d} median_3d_mm{coil_state.median_3d_mm} {int(c)}")
        else:
            pass
        c=int(max(c,0))
        return c,c

    def vstack_by_distance(self,new_image_list):
        coil_state = get_coilState(self.coil_id,self.config.surface_key)
        if coil_state is None:
            return np.vstack(new_image_list)
        clip_nums=self.get_num_clip_by_mm(coil_state,coil_state.median_3d_mm)

        return np.vstack([new_image_list[0],new_image_list[1][clip_nums[0]:,:], new_image_list[2][clip_nums[1]:,:]])

    def _join_images_(self,image_list, coil_id):
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

        max_image=self.vstack_by_distance(new_image_list)
        # result = np.vstack(new_image_list)
        # cv2.imwrite("s.jpg", result)
        if DEBUG:
            im_show(max_image,title=fr"max_image{self.key}_{coil_id}")
        return max_image

    def run(self):
        print(fr" SurfaceWork run {self.key}")
        self.cameras_wolk = [CameraWork(config) for config in self.config.camera_configs]

        while self._run_:
            coil_id = self.queue_in.get()
            di = DataIntegration(self.config, coil_id)

            image_dict = {}
            for camera_wolk in self.cameras_wolk:
                camera_wolk.add_work(coil_id)
            for camera_wolk in self.cameras_wolk:
                image_dict[camera_wolk.config.key[6]] = camera_wolk.get()
            try:
                max_image = self.join_images(image_dict,coil_id)
                if max_image is not None:
                    di.set_max_image(max_image)
                    detection(di)
                    self.save_wolk.add_work([coil_id, max_image])
            except AttributeError as e:
                logger.error(f"AttributeError: {e} - {self.key} - {coil_id}")
                # raise e
                if DEBUG:
                    raise e
            except BaseException as e:
                logger.error(e)
                if DEBUG:
                    raise e
            self.set(None)