from typing import List

import cv2
import numpy as np

from algorithm_runtime_2D.JoinService.cv_count_tool import get_intersections, hconcat_list, im_show
from algorithm_runtime_2D.area_alg.YoloModelResults import YoloModelSegResults
from algorithm_runtime_2D.configs import CONFIG
from algorithm_runtime_2D.configs.CONFIG import DEBUG
from algorithm_runtime_2D.configs.CameraConfig import CameraConfig
from algorithm_runtime_2D.configs.DebugConfigs import debug_config
from algorithm_runtime_2D.utils.MultiprocessColorLogger import logger


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
                debug_config.save_simple_image(draw_image, f"seg_{self.config.key}_{self.coil_id}_{i}.jpg")

                mask_image = seg_result.get_mask()
                if mask_image is not None:
                    try:
                        debug_config.save_mask_image(mask_image, f"mask_{self.config.key}_{self.coil_id}_{i}.jpg")
                    except Exception as e:
                        logger.warning("Error saving mask image: %s", e)

        raw_masks = []
        self.image_list = []
        for seg_result in results:
            seg_result: "YoloModelSegResults"
            raw_masks.append(seg_result.get_mask())
            self.image_list.append(seg_result.image)

        valid_mask = next((mask for mask in raw_masks if mask is not None and mask.size), None)
        if valid_mask is not None:
            mask_shape = valid_mask.shape[:2]
        else:
            mask_size = max(int(round(self.config.surface_config.image_size / self.config.surface_config.scale)), 1)
            mask_shape = (mask_size, mask_size)

        self.mask_list = []
        for mask in raw_masks:
            if mask is None or not mask.size:
                normalized_mask = np.zeros(mask_shape, dtype=np.uint8)
            else:
                normalized_mask = np.asarray(mask)
                if normalized_mask.ndim == 3:
                    normalized_mask = normalized_mask.max(axis=2)
                if normalized_mask.shape != mask_shape:
                    normalized_mask = cv2.resize(
                        normalized_mask,
                        (mask_shape[1], mask_shape[0]),
                        interpolation=cv2.INTER_NEAREST,
                    )
                normalized_mask = np.where(normalized_mask > 0, 255, 0).astype(np.uint8)
            self.mask_list.append(normalized_mask)

        for seg_result in results:
            seg_result.result = None
        self.results = None

        self.format_images()

        self.mask_intersections = get_intersections(
            self.mask_list,
            fr"{self.coil_id}_{self.config.surface_key}_{self.config.key}",
        )
        self.intersections = []
        for index, intersection in enumerate(self.mask_intersections):
            image_width = self.image_list[index + 1].shape[1]
            mask_width = self.mask_list[index + 1].shape[1]
            self.intersections.append(int(round(intersection * image_width / mask_width)))


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

        logger.debug(
            "mask_list %s format_images %s left=%s right=%s",
            len(self.mask_list),
            in_list,
            left_index,
            right_index,
        )

        self.left_index = left_index
        self.right_index = right_index

        # self.mask_list = self.mask_list[left_index:right_index+1]
        # self.image_list = self.image_list[left_index:right_index+1]

    def init_image(self):
        image_count = len(self.image_list)
        if image_count == 0:
            self.intersections = []
            self.mask_intersections = []
            return

        raw_left_index = 0 if self.left_index is None else self.left_index
        raw_right_index = image_count - 1 if self.right_index is None else self.right_index
        left_index = min(max(int(raw_left_index), 0), image_count - 1)
        right_index = min(max(int(raw_right_index), left_index), image_count - 1)
        self.intersections = self.intersections[left_index:right_index]
        self.mask_intersections = self.mask_intersections[left_index:right_index]
        self.mask_list = self.mask_list[left_index:right_index + 1]
        self.image_list = self.image_list[left_index:right_index + 1]

        required_intersections = max(len(self.image_list) - 1, 0)
        self.intersections = self.intersections[:required_intersections]
        self.mask_intersections = self.mask_intersections[:required_intersections]
        self.intersections.extend([0] * (required_intersections - len(self.intersections)))
        self.mask_intersections.extend([0] * (required_intersections - len(self.mask_intersections)))

    def set_intersections(self,new_):
        "设置统一的 参数"
        self.set_stitching(new_.left_index, new_.right_index, new_.intersections)

    def set_stitching(self, left_index, right_index, intersections):
        self.intersections = list(intersections)
        self.mask_intersections = []
        for index, intersection in enumerate(self.intersections):
            if index + 1 >= len(self.image_list) or index + 1 >= len(self.mask_list):
                self.mask_intersections.append(0)
                continue
            image_width = self.image_list[index + 1].shape[1]
            mask_width = self.mask_list[index + 1].shape[1]
            self.mask_intersections.append(int(round(intersection * mask_width / image_width)))
        self.left_index = left_index
        self.right_index = right_index

    def join_image(self):

        # if DEBUG:
        #     self.intersections=[440 for i in self.intersections]


        logger.debug("intersections %s %s %s", self.coil_id, self.config.key, self.intersections)
        image = hconcat_list(self.image_list, self.intersections,False)
        # im_show(image, fr"join_image {self.config.key}")

        if DEBUG:
            im_show(image,fr"join_image {self.config.key}")

        return image

    def join_mask(self):
        mask = hconcat_list(self.mask_list, self.mask_intersections, False)
        if mask is None:
            return None
        if mask.ndim == 3:
            mask = mask.max(axis=2)
        return np.where(mask > 0, 255, 0).astype(np.uint8)

    def release_images(self) -> None:
        """Release decoded 5120px source frames after their row is joined."""
        self.image_list.clear()

    def release_masks(self) -> None:
        """Release segmentation masks after their row is joined."""
        self.mask_list.clear()

    def release(self) -> None:
        self.release_images()
        self.release_masks()
        self.results = None
