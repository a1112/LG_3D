import os
import time
from threading import BoundedSemaphore
from typing import Dict

import cv2
import numpy as np

from algorithm_runtime_2D.configs.CONFIG import DEBUG
from algorithm_runtime_2D.configs.SurfaceConfig import SurfaceConfig
from algorithm_runtime_2D.utils.MultiprocessColorLogger import logger
from algorithm_runtime_2D.utils.model_memory import release_inference_caches

from algorithm_runtime_2D.property.CameraImageGrop import CameraImageGrop

from algorithm_runtime_2D.property.DataIntegration import DataIntegration

from .WorkBase import WorkBaseThread
from .CameraWork import CameraWork
from .SaverWork import SaverWork
from .cv_count_tool import im_show
from algorithm_runtime_2D.alg_2d.detection import detection, persist_detection_results
from CoilDataBase.Coil import get_coilState


def _float_env(name: str, default: float) -> float:
    raw_value = os.getenv(name, str(default))
    try:
        return max(float(raw_value), 1.0)
    except ValueError:
        logger.warning("invalid %s=%s, use %s", name, raw_value, default)
        return default


def _int_env(name: str, default: int, minimum: int = 0) -> int:
    raw_value = os.getenv(name, str(default))
    try:
        return max(int(raw_value), minimum)
    except ValueError:
        logger.warning("invalid %s=%s, use %s", name, raw_value, default)
        return default


CAMERA_RESULT_TIMEOUT = _float_env("ALG_2D_CAMERA_RESULT_TIMEOUT", 120.0)
AREA_SAVE_QUEUE_TIMEOUT = _float_env("ALG_2D_AREA_SAVE_QUEUE_TIMEOUT", 30.0)
AREA_SAVE_RESULT_TIMEOUT = _float_env("ALG_2D_AREA_SAVE_RESULT_TIMEOUT", 180.0)
SOURCE_QUIET_SECONDS = _float_env("ALG_2D_SOURCE_QUIET_SECONDS", 10.0)
MIN_IMAGES_PER_CAMERA = _int_env("ALG_2D_MIN_IMAGES_PER_CAMERA", 2, 1)
MAX_CAMERA_COUNT_SKEW = _int_env("ALG_2D_MAX_CAMERA_COUNT_SKEW", 2)
SURFACE_PIPELINE_SEMAPHORE = BoundedSemaphore(
    _int_env("ALG_2D_SURFACE_PIPELINE_CONCURRENCY", 1, 1))


def _camera_position_key(camera_work: CameraWork) -> str:
    key = str(camera_work.config.key)
    position = key.rsplit("_", 1)[-1]
    if position in {"U", "M", "D"}:
        return position
    logger.warning("2D camera key has unexpected format: %s", key)
    return key


class SurfaceWork(WorkBaseThread):
    """
    单表面
    """
    def __init__(self,key,config:SurfaceConfig):
        self.key = key
        super().__init__(config, deduplicate=True)
        self.config:SurfaceConfig


        self.save_wolk = SaverWork(self.config)
        self.cameras_wolk = [
            CameraWork(camera_config)
            for camera_config in self.config.camera_configs
        ]
        self.start()

    def _child_workers(self):
        return (*tuple(self.cameras_wolk), self.save_wolk)

    def get_intersections(self,camera_image_grop_dict):
        left_index = min([item.left_index for item in camera_image_grop_dict])
        right_index = max([item.right_index for item in camera_image_grop_dict])

        # Source frames can be missing independently for each camera, so the
        # same list index does not necessarily represent the same capture
        # time.  Median-merging by index therefore creates false overlaps.
        upper_group = camera_image_grop_dict[0]
        middle_group = camera_image_grop_dict[1]
        intersections = list(middle_group.intersections)
        upper_left = max(int(upper_group.left_index or 0), 0)
        upper_right = min(
            int(upper_group.right_index
                if upper_group.right_index is not None else
                len(upper_group.intersections)),
            len(upper_group.intersections),
        )
        for index in range(upper_left, upper_right):
            if index < len(intersections):
                intersections[index] = upper_group.intersections[index]
            else:
                intersections.append(upper_group.intersections[index])
        return intersections, left_index, right_index

    def join_images(self, camera_image_grop_dict: Dict[str, CameraImageGrop],
                    coil_id):
        camera_image_grop_list = [
            camera_image_grop_dict["U"], camera_image_grop_dict["M"],
            camera_image_grop_dict["D"]
        ]

        intersections,left_index,right_index = self.get_intersections(camera_image_grop_list)
        camera_image_grop_dict["U"].set_stitching(left_index, right_index, intersections)
        camera_image_grop_dict["M"].set_intersections(camera_image_grop_dict["U"])
        camera_image_grop_dict["D"].set_intersections(camera_image_grop_dict["U"])

        camera_image_grop_dict["U"].init_image()
        camera_image_grop_dict["M"].init_image()
        camera_image_grop_dict["D"].init_image()
        joined_images = []
        try:
            for camera_image_grop in camera_image_grop_list:
                joined_images.append(camera_image_grop.join_image())
                camera_image_grop.release_images()
            max_image = self._join_images_(joined_images, coil_id)
        finally:
            # Each camera group may own up to ten decoded 5120x5120 RGB
            # frames.  Once its row is joined, those source arrays are no
            # longer needed by mask joining or surface detection.
            for camera_image_grop in camera_image_grop_list:
                camera_image_grop.release_images()
            joined_images.clear()
        max_mask = None
        joined_masks = []
        try:
            for camera_image_grop in camera_image_grop_list:
                joined_masks.append(camera_image_grop.join_mask())
                camera_image_grop.release_masks()
            max_mask = self._join_masks_(joined_masks, coil_id,
                                         target_shape=max_image.shape[:2]
                                         if max_image is not None else None)
        except Exception as e:
            logger.exception(
                "2D surface %s mask join failed coil_id=%s: %s", self.key,
                coil_id, e)
        finally:
            for camera_image_grop in camera_image_grop_list:
                camera_image_grop.release_masks()
            joined_masks.clear()
        return max_image, max_mask

    def get_num_clip_by_mm(self,coil_state,median_3d_mm):
        """
        获取裁剪系数
        """
        if self.config.clip_mode == "fixed" or coil_state is None or median_3d_mm is None:
            fixed = max(int(self.config.clip_fixed), 0)
            return fixed, fixed

        a = self.config.clip_dynamic_a
        b = self.config.clip_dynamic_b
        c_base = self.config.clip_dynamic_c
        c = (median_3d_mm - c_base) * a + b
        c2 = c + self.config.clip_dynamic_offset
        c = int(max(c, 0))
        c2 = int(max(c2, 0))
        return c, c2

    def vstack_by_distance(self, new_image_list, coil_id, scale: float = 1.0):
        coil_state = get_coilState(coil_id,self.config.surface_key)
        median_3d_mm = coil_state.median_3d_mm if coil_state is not None else None
        clip_nums = self.get_num_clip_by_mm(coil_state, median_3d_mm)
        clip_nums = tuple(max(int(round(value / scale)), 0) for value in clip_nums)

        return np.vstack([
            new_image_list[0], new_image_list[1][clip_nums[0]:, :],
            new_image_list[2][clip_nums[1]:, :]
        ])

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

        max_image=self.vstack_by_distance(new_image_list, coil_id)
        # result = np.vstack(new_image_list)
        # cv2.imwrite("s.jpg", result)
        if DEBUG:
            im_show(max_image,title=fr"max_image{self.key}_{coil_id}")
        return max_image

    def _join_masks_(self, mask_list, coil_id, target_shape=None):
        max_width = max(
            [img.shape[1] for img in mask_list if img is not None] + [0])
        if max_width <= 0:
            return None
        new_mask_list = []
        for img in mask_list:
            if img is None:
                img = np.zeros((self.config.image_size, max_width), np.uint8)
            if img.ndim == 3:
                img = img.max(axis=2)
            if img.shape[1] < max_width:
                padding = max_width - img.shape[1]
                img = cv2.copyMakeBorder(img, 0, 0, 0, padding, cv2.BORDER_CONSTANT, value=0)
            elif img.shape[1] > max_width:
                img = img[:, :max_width]
            new_mask_list.append(img)

        max_mask = self.vstack_by_distance(new_mask_list, coil_id, scale=self.config.scale)
        if max_mask is None:
            return None
        max_mask = np.asarray(max_mask, dtype=np.uint8)
        max_mask[max_mask > 0] = 255
        if target_shape is not None and max_mask.shape != tuple(target_shape):
            max_mask = cv2.resize(
                max_mask,
                (target_shape[1], target_shape[0]),
                interpolation=cv2.INTER_NEAREST,
            )
        if DEBUG:
            im_show(max_mask, title=fr"max_mask{self.key}_{coil_id}")
        return max_mask

    def run(self):
        logger.info("2D surface %s worker started", self.key)

        while True:
            work_request = self.get_next_work()
            if work_request is None:
                break
            coil_id = self.get_work_value(work_request)
            self.mark_started(work_request)
            surface_succeeded = False
            image_dict = {}
            camera_image_grop = None
            di = None
            defect_list = None
            max_image = None
            max_mask = None
            pipeline_slot_acquired = False
            try:
                # S and L each transiently own gigabytes of decoded and joined
                # image data.  Keep the complete surface lifecycle, including
                # asynchronous AREA saving, within one bounded memory slot.
                SURFACE_PIPELINE_SEMAPHORE.acquire()
                pipeline_slot_acquired = True
                logger.info("2D surface %s start coil_id=%s", self.key, coil_id)
                source_snapshot = self.config.get_source_snapshot(coil_id)
                if not self.config.source_snapshot_complete(
                        source_snapshot,
                        min_images_per_camera=MIN_IMAGES_PER_CAMERA,
                        max_camera_count_skew=MAX_CAMERA_COUNT_SKEW,
                        quiet_seconds=SOURCE_QUIET_SECONDS,
                ):
                    logger.info(
                        "2D surface %s deferred incomplete or changing input coil_id=%s",
                        self.key,
                        coil_id,
                    )
                    continue

                submitted_cameras = []
                for camera_wolk in self.cameras_wolk:
                    ticket = camera_wolk.add_work(coil_id)
                    if ticket:
                        submitted_cameras.append((camera_wolk, ticket))
                    else:
                        image_dict[_camera_position_key(camera_wolk)] = None

                deadline = time.monotonic() + CAMERA_RESULT_TIMEOUT
                for camera_wolk, ticket in submitted_cameras:
                    position_key = _camera_position_key(camera_wolk)
                    remaining = max(deadline - time.monotonic(), 0.0)
                    camera_image_grop = camera_wolk.get(
                        timeout=remaining,
                        expected_ticket=ticket,
                    )
                    image_dict[position_key] = camera_image_grop

                expected_keys = [
                    _camera_position_key(camera_wolk)
                    for camera_wolk in self.cameras_wolk
                ]
                missing_keys = [
                    key for key in expected_keys
                    if image_dict.get(key) is None
                ]
                if missing_keys:
                    logger.warning(
                        "2D surface %s skipped incomplete cameras coil_id=%s missing=%s",
                        self.key,
                        coil_id,
                        ",".join(missing_keys),
                    )
                    continue

                if self.config.get_source_snapshot(coil_id) != source_snapshot:
                    logger.warning(
                        "2D surface %s input changed during load coil_id=%s",
                        self.key, coil_id)
                    continue

                di = DataIntegration(self.config, coil_id)
                max_image, max_mask = self.join_images(image_dict,coil_id)
                image_dict.clear()
                camera_image_grop = None
                if max_image is not None:
                    di.set_max_image(max_image)
                    defect_list = detection(di, persist=False)
                    if self.config.get_source_snapshot(coil_id) != source_snapshot:
                        logger.warning(
                            "2D surface %s input changed during processing coil_id=%s",
                            self.key, coil_id)
                        continue
                    persist_detection_results(di, defect_list)
                    save_ticket = self.save_wolk.add_work(
                        [coil_id, max_image, max_mask],
                        timeout=AREA_SAVE_QUEUE_TIMEOUT,
                    )
                    if save_ticket:
                        logger.info(
                            "2D surface %s queued AREA save coil_id=%s",
                            self.key, coil_id)
                        # Transfer ownership to SaverWork before waiting.  This
                        # lets its completion release the only remaining large
                        # array references inside the serialized memory slot.
                        di.max_image = None
                        max_image = None
                        max_mask = None
                        if self.save_wolk.wait_for_completion(
                                coil_id,
                                timeout=AREA_SAVE_RESULT_TIMEOUT,
                        ):
                            surface_succeeded = self.config.area_output_complete(
                                coil_id)
                            if not surface_succeeded:
                                logger.error(
                                    "2D surface %s AREA save incomplete coil_id=%s",
                                    self.key,
                                    coil_id,
                                )
                        else:
                            logger.error(
                                "2D surface %s AREA save timeout coil_id=%s "
                                "timeout=%ss",
                                self.key,
                                coil_id,
                                AREA_SAVE_RESULT_TIMEOUT,
                            )
                    else:
                        logger.error(
                            "2D surface %s AREA save queue full coil_id=%s",
                            self.key, coil_id)
                else:
                    logger.warning(
                        "2D surface %s skipped empty image coil_id=%s",
                        self.key, coil_id)
            except AttributeError as e:
                logger.error("AttributeError: %s - %s - %s", e, self.key, coil_id)
                if DEBUG:
                    raise
            except Exception as e:
                logger.exception("2D surface %s failed coil_id=%s: %s",
                                 self.key, coil_id, e)
                if DEBUG:
                    raise
            finally:
                self.set(surface_succeeded, work_request=work_request)
                self.mark_finished(work_request)
                self.queue_in.task_done()
                image_dict.clear()
                camera_image_grop = None
                di = None
                defect_list = None
                max_image = None
                max_mask = None
                try:
                    release_inference_caches()
                finally:
                    if pipeline_slot_acquired:
                        SURFACE_PIPELINE_SEMAPHORE.release()
