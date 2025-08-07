from typing import List

import numpy as np

from JoinService.cv_count_tool import get_intersections, hconcat_list, im_show
from area_alg.YoloModelResults import YoloModelSegResults
from configs import CONFIG
from configs.CONFIG import DEBUG
from configs.CameraConfig import CameraConfig
from configs.DebugConfigs import debug_config


def _image_line_has_data_(line:np.ndarray) -> bool:
    return len(line.nonzero()[0])>30


def _image_all_in_(gray_image):
    h,w = gray_image.shape[:2]
    return _image_line_has_data_(gray_image[:, 2:3]), _image_line_has_data_(gray_image[:, w-3:w-2])


class CameraImageGrop:
    def __init__(self, coil_id, config:CameraConfig, results:List[YoloModelSegResults]):
        self.right_index = None
        self.left_index = None
        self.results = results
        self.config = config
        self.coil_id = coil_id
        if CONFIG.DEBUG:
            for i, seg_result in enumerate(results):
                draw_image = seg_result.get_draw()
                debug_config.save_simple_image(draw_image, f"seg_{self.config.key}_{i}.jpg")

                mask_image = seg_result.get_mask()
                if mask_image is not None:
                    try:
                        debug_config.save_mask_image(mask_image, f"mask_{self.config.key}_{i}.jpg")
                    except Exception as e:
                        print(f"Error saving mask image: {e}")


        self.mask_list=[]
        self.image_list=[]
        for seg_result in results:
            seg_result: "YoloModelSegResults"
            mask = seg_result.get_mask()
            if mask is not None:
                self.mask_list.append(mask)
            else:
                self.mask_list.append(np.zeros(seg_result.image.shape[:2]))

            self.image_list.append(seg_result.image)

        self.format_images()

        self.intersections = get_intersections(self.mask_list)
        self.intersections = [i * self.config.surface_config.scale for i in self.intersections]


        # for mask, image in zip(self.mask_list, self.image_list):
            # im_show(mask, fr"mask {self.config.key}")
            # im_show(image, fr"image {self.config.key}")

    def format_images(self):
        left_index=0
        right_index=len(self.mask_list)-1

        in_list=[]
        for mask in self.mask_list:
            in_list.append(_image_all_in_(mask))

        for i in range(len(in_list)):
            if in_list[i][0] and (i-1<0 or not in_list[i-1][0]):
                left_index = max(i-1,0)
                break

        for i in range(len(in_list))[::-1]:
            if in_list[i][1] and (i + 1 >= len(in_list) or not in_list[i + 1][1]):
                right_index = i+1
                break

        print(fr"mask_list {len(self.mask_list)} format_images {in_list} {left_index} {right_index}")

        self.left_index = left_index
        self.right_index = right_index

        # self.mask_list = self.mask_list[left_index:right_index+1]
        # self.image_list = self.image_list[left_index:right_index+1]

    def init_image(self):
        self.intersections=self.intersections[self.left_index:self.right_index]
        self.mask_list = self.mask_list[self.left_index:self.right_index + 1]
        self.image_list = self.image_list[self.left_index:self.right_index + 1]

    def set_intersections(self,new_):
        "设置统一的 参数"
        self.intersections = new_.intersections
        self.left_index = new_.left_index
        self.right_index = new_.right_index

    def join_image(self):

        # if DEBUG:
        #     self.intersections=[440 for i in self.intersections]


        print(fr"intersections {self.coil_id} {self.config.key} {self.intersections}")
        image = hconcat_list(self.image_list, self.intersections)

        if DEBUG:
            im_show(image,fr"join_image {self.config.key}")

        return image