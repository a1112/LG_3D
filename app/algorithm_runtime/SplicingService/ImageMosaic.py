import asyncio
import json
import traceback
import time
from pathlib import Path
import logging
from typing import List, Optional
import six

import cv2
import numpy as np
from PIL import Image

# import AlarmDetection
from Save3D.save import D3Saver

from Base.property.ErrorBase import ServerDetectionException
from utils.DetectionSpeedRecord import DetectionSpeedRecord
from Base.tools import tool  # FlattenSurface

from Base.CONFIG import isLoc, serverConfigProperty
from Init import ColorMaps, PreviewSize
from .DataFolder import DataFolder
from .ImageSaver import ImageSaver
from .depth_plane import align_camera_depth_planes
from .taper_error_threshold import taper_error_threshold_from_limits
from Globs import control
from Base.property.Base import DataIntegration

from Base.utils.Log import logger
from Base.utils.LoggerProcess import LoggerProcess

import Globs


def leveling_2d(datas):
    if Globs.control.leveling_gray:  # 调整灰度
        media_gray_list = []
        for data in datas:
            image_2d = data.get("2D")
            if image_2d is None or image_2d.size == 0:
                logger.warning(
                    f"leveling_2d skip empty image: camera={data.get('camera')}"
                )
                return
            valid_gray = image_2d[image_2d != 0]
            if valid_gray.size == 0:
                logger.warning(
                    f"leveling_2d skip all-zero image: camera={data.get('camera')}"
                )
                return
            media_gray = float(np.median(valid_gray))
            media_gray_list.append(media_gray)
        logger.debug("leveling_2d medians=%s", media_gray_list)
        if len(media_gray_list) < 3 or media_gray_list[1] <= 0:
            logger.warning(f"leveling_2d skip invalid medians: {media_gray_list}")
            return
        ratio_list = [gray / media_gray_list[1] for gray in media_gray_list]
        if min(ratio_list) < 0.4 or max(ratio_list) > 2.5:
            logger.error(
                f"leveling_2d 失败: medians={media_gray_list}, ratios={ratio_list}"
            )
            return
        for index in (0, 2):
            if media_gray_list[index] <= 0:
                continue
            scale = media_gray_list[1] / media_gray_list[index]
            datas[index]["2D"] = np.clip(
                datas[index]["2D"].astype(np.float32) * scale, 0,
                255).astype(np.uint8)


class ImageMosaic(Globs.control.BaseImageMosaic):
    """
    单表面处理
    """
    def __init__(self, config, managerQueue, logger_process: LoggerProcess):
        super().__init__()
        self._running = True
        self.dataFolderList: List[DataFolder] = []
        self.d3Saver: Optional[D3Saver] = None
        self.imageSaver: Optional[ImageSaver] = None
        self.managerQueue = managerQueue
        self.currentSecondaryCoil = None
        self.colorImageDict = {}
        self.loggerProcess = logger_process
        self.config = config
        self.key = config["key"]
        self.saveFolder = Path(config["saveFolder"])
        self.rotate = config["rotate"]
        self.direction = config["direction"]
        self.x_rotate = config["x_rotate"]
        self.save3D_data = bool(config.get("save3D_data", True))
        self.save = True
        self.saveFolder.mkdir(parents=True, exist_ok=True)
        self.dataList = []
        self.start()

    def setSave(self, save: bool):
        self.save = save

    def _save_(self, image, path):
        if self.save:
            return self.imageSaver.add(image, path)
        return None

    def set_coil_id(self, coil_id):
        coil_id = str(coil_id)
        if not self.has_data(coil_id):
            return False
        (self.saveFolder / coil_id).mkdir(parents=True, exist_ok=True)
        self.producer.put(coil_id)
        return True

    def _save_image_(self, data_integration, image, name):
        from pathlib import Path

        cache_image = image.copy()

        # 保存 PNG
        self._save_(image, data_integration.get_save_url("png", name + serverConfigProperty.save_image_type))

        # 保存 JPG（用于缓存生成）
        jpg_path = Path(data_integration.get_save_url("jpg", name + ".jpg"))
        self._save_(image, jpg_path)

        # 保存 MASK PNG
        image_rgba = image.convert("RGBA")
        image_rgba.putalpha(data_integration.pil_mask)
        self._save_(image_rgba, data_integration.get_save_url("mask", name + ".png"))

        # 保存预览
        image = image.copy()
        image.thumbnail(PreviewSize)
        self._save_(image, data_integration.get_save_url("preview", name + ".jpg"))

        # ========== 生成缩略图缓存（在 jpg 目录下） ==========
        try:
            from Base.utils.cache_generator import generate_gray_thumbnail, generate_jet_thumbnail

            coil_id = data_integration.coilId
            surface_key = data_integration.surface

            # 缓存目录：{saveFolder}/{surface_key}/{coil_id}/jpg/cache/
            cache_base = Path(data_integration.get_save_url("jpg", "")) / "cache"

            # GRAY 缓存：从 GRAY.jpg 生成
            if name == "GRAY":
                gray_cache_dir = cache_base / "falsecolor" / "gray"
                generate_gray_thumbnail(
                    source_pil_image=cache_image,
                    cache_dir=gray_cache_dir,
                    size=1024
                )
                logger.info(f"Generated GRAY cache for {surface_key}/{coil_id}")

            # JET 缓存：从 JET.jpg 生成（如果 JET 图像存在）
            elif name == "JET":
                jet_cache_dir = cache_base / "falsecolor" / "jet"
                generate_jet_thumbnail(
                    source_pil_image=cache_image,
                    cache_dir=jet_cache_dir,
                    size=1024
                )
                logger.info(f"Generated JET cache for {surface_key}/{coil_id}")

        except Exception as e:
            logger.error(f"Failed to generate cache for {name}: {e}")

    # 保存图像
    async def save_image(self, data_integration: DataIntegration):
        self._save_image_(data_integration, data_integration.pil_image, "GRAY")
        self._save_image_(data_integration, data_integration.pil_mask, "MASK")

    async def save_json(self, data_integration: DataIntegration):
        coil_id = data_integration.coilId
        data = data_integration.export_json()
        with open(self.saveFolder / coil_id / "data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    async def save3_d(self, data_integration: DataIntegration):
        config_datas = data_integration.configDatas
        circle_config = data_integration.circle_config
        mask_image = data_integration.npy_mask
        coil_id = data_integration.coilId

        start = data_integration.median_non_zero + serverConfigProperty.colorFromValue_mm // data_integration.scan3dCoordinateScaleZ
        self._save_(data_integration.npy_data, self.saveFolder / coil_id / "3D.npz")
        step = (serverConfigProperty.colorToValue_mm - serverConfigProperty.colorFromValue_mm) // data_integration.scan3dCoordinateScaleZ
        data_integration.set("colorFromValue_mm", serverConfigProperty.colorFromValue_mm)
        data_integration.set("colorToValue_mm", serverConfigProperty.colorToValue_mm)
        data_integration.set("start", start)
        data_integration.set("step", step)
        self.colorImageDict = {}
        data_integration.set_telescoped_alarms()
        npy__ = data_integration.npy_data
        non_zero_elements = npy__[npy__ != 0]
        a, b = start, start + step
        depth_map_clipped = np.clip(npy__, a, b)
        depth_map_scaled = ((depth_map_clipped - a) / (b - a)) * -255 + 255
        depth_map_uint8 = depth_map_scaled.astype(np.uint8)
        mask_zero = npy__ == 0
        for name, colormap in ColorMaps.items():
            if name not in serverConfigProperty.renderer_list:
                continue
            depth_map_color = cv2.applyColorMap(depth_map_uint8, colormap)
            depth_map_color[mask_zero] = [0, 0, 0]  # [0, 0, 0] 表示黑色

            image = Image.fromarray(depth_map_color)
            self._save_image_(data_integration, image, name)
            self.colorImageDict[name] = image

        # ========== 生成 Error 塔形报警图像 ==========
        try:
            from Base.utils.cache_generator import generate_error_image, get_error_cache_dir

            # 保存 3D.npz 的路径
            npy_file = self.saveFolder / coil_id / "3D.npz"

            # median_z_int 用于计算阈值偏移
            median_z_int = int(data_integration.median_non_zero) if data_integration.median_non_zero else 0
            threshold_down, threshold_up = self._get_taper_error_thresholds(data_integration)

            # png 目录用于保存 Error.png
            png_dir = get_error_cache_dir(str(npy_file))
            generate_error_image(
                npy_data=npy__,
                png_dir=png_dir,
                median_z_int=median_z_int,
                threshold_down=threshold_down,
                threshold_up=threshold_up,
                scale_factor=data_integration.scan3dCoordinateScaleZ
            )
            logger.info(f"Generated Error image for {data_integration.key}/{coil_id}")
        except Exception as e:
            logger.error(f"Failed to generate Error image: {e}")

        obj_file = self.saveFolder / coil_id / "3D.obj"
        if self.save3D_data:
            self.d3Saver.add_([
                coil_id,
                npy__,
                mask_image,
                config_datas,
                circle_config,
                obj_file,
                data_integration.median_3d_mm,
                data_integration.get_bd_xyz(),
            ])
        return non_zero_elements

    def join_saver(self):
        self.imageSaver.join()

    def _get_taper_error_thresholds(self, data_integration: DataIntegration):
        default_threshold = 60
        try:
            from AlarmDetection.property import alarmConfigProperty

            _, height_limits, _, _, _ = alarmConfigProperty.get_taper_shape_config(
                data_integration
            ).get_config().get_config()
            return taper_error_threshold_from_limits(height_limits)
        except Exception as e:
            logger.warning(f"get taper error thresholds failed, use default {default_threshold}: {e}")
        return default_threshold, default_threshold

    @DetectionSpeedRecord.timing_decorator("数据获取 __getAllData__")
    def __getAllData__(self, data_integration):
        # 设置 任务
        """
        对于最新的数据，应该同步完成，缺乏实时模式
        Args:
            data_integration:

        Returns:

        """
        common_stems = self._get_common_valid_stems(data_integration.coilId)
        for dataFolder in self.dataFolderList:
            dataFolder.set_coil_id(data_integration.coilId, common_stems)
        #  获取数据
        datas = []
        config_datas = []
        for dataFolder in self.dataFolderList:  # 获取所有的图片
            data = dataFolder.get_data()
            datas.append(data)
            try:
                config_datas.append(data["json"])
            except KeyError:
                logger.warning(
                    f"config data missing: coil={data_integration.coilId}, surface={self.key}, "
                    f"camera={dataFolder.folderName}"
                )
        #   待修改，使用工具类型进行封装
        data_integration.datas, data_integration.configDatas = datas, config_datas

    def _get_common_valid_stems(self, coil_id):
        valid_stem_sets = []
        for dataFolder in self.dataFolderList:
            try:
                stems = dataFolder.get_valid_3d_stems(str(coil_id))
            except Exception as e:
                logger.warning(
                    f"get valid 3D stems failed: coil={coil_id}, surface={self.key}, "
                    f"camera={dataFolder.folderName}, error={e}"
                )
                return None
            if not stems:
                logger.warning(
                    f"no valid 3D stems: coil={coil_id}, surface={self.key}, "
                    f"camera={dataFolder.folderName}"
                )
                return None
            valid_stem_sets.append({str(stem) for stem in stems})

        common = set.intersection(*valid_stem_sets) if valid_stem_sets else set()
        common_stems = sorted(common, key=lambda stem: int(stem) if stem.isdigit() else stem)
        if len(common_stems) < 2:
            logger.warning(
                f"too few common valid 3D stems: coil={coil_id}, surface={self.key}, stems={common_stems}"
            )
            return None
        logger.warning(
            f"use common valid 3D stems: coil={coil_id}, surface={self.key}, stems={common_stems}"
        )
        return common_stems

    def raise_error(self, message):
        raise ServerDetectionException(message)

    @DetectionSpeedRecord.timing_decorator("拼接图像计时")
    def __stitching__(self, data_integration: DataIntegration):
        min_h = None
        max_h = None
        valid_datas = []
        datas = data_integration.datas
        for data in datas:
            camera = data.get("camera", "unknown")
            missing_keys = [
                key for key in ["2D", "MASK", "3D"]
                if key not in data or data[key] is None
            ]
            if missing_keys:
                logger.warning(
                    f"skip camera data with missing keys: coil={data_integration.coilId}, "
                    f"surface={data_integration.surface}, camera={camera}, missing={missing_keys}"
                )
                continue
            if any(data[key].size == 0 for key in ["2D", "MASK", "3D"]):
                logger.warning(
                    f"skip camera data with empty image: coil={data_integration.coilId}, "
                    f"surface={data_integration.surface}, camera={camera}, "
                    f"shapes={{'2D': {data['2D'].shape}, 'MASK': {data['MASK'].shape}, '3D': {data['3D'].shape}}}"
                )
                continue

            image_h = data["2D"].shape[0]
            rec = data.get("rec")
            if rec and len(rec) >= 4 and rec[3] > 0:
                top = max(0, int(rec[1]))
                bottom = min(image_h, top + int(rec[3]))
            else:
                logger.warning(
                    f"steel rect missing, use full image height: coil={data_integration.coilId}, "
                    f"surface={data_integration.surface}, camera={camera}, crop_rec={data.get('crop_rec')}"
                )
                top = 0
                bottom = image_h
            if bottom <= top:
                logger.warning(
                    f"invalid crop range, use full image height: coil={data_integration.coilId}, "
                    f"surface={data_integration.surface}, camera={camera}, top={top}, bottom={bottom}"
                )
                top = 0
                bottom = image_h
            min_h = top if min_h is None else min(min_h, top)
            max_h = bottom if max_h is None else max(max_h, bottom)
            valid_datas.append(data)

        if not valid_datas or min_h is None or max_h is None or max_h <= min_h:
            self.raise_error(
                f"算法错误：{data_integration.surface} 面无有效相机数据，coil={data_integration.coilId}"
            )

        datas = valid_datas
        out_side_px = Globs.control.out_side_px
        crop_top = max(min_h - out_side_px, 0)
        crop_datas = []
        for data in datas:  # 裁剪，减低计算
            camera = data.get("camera", "unknown")
            crop_bottom = min(max_h + out_side_px, data["2D"].shape[0])
            if crop_bottom <= crop_top:
                logger.warning(
                    f"skip camera data after crop: coil={data_integration.coilId}, "
                    f"surface={data_integration.surface}, camera={camera}, "
                    f"crop_top={crop_top}, crop_bottom={crop_bottom}"
                )
                continue
            for key in ["2D", "MASK", "3D"]:
                data[key] = data[key][crop_top:crop_bottom, :]
            if data["MASK"].size == 0 or not np.any(data["MASK"] > 150):
                logger.warning(
                    f"skip camera data with empty mask foreground: coil={data_integration.coilId}, "
                    f"surface={data_integration.surface}, camera={camera}, mask_shape={data['MASK'].shape}"
                )
                continue
            crop_datas.append(data)

        if not crop_datas:
            self.raise_error(
                f"算法错误：{data_integration.surface} 面裁剪后无有效 mask，coil={data_integration.coilId}"
            )

        datas = crop_datas
        data_integration.datas = datas
        camera_plane_alignments = align_camera_depth_planes(
            datas,
            data_integration.scan3dCoordinateScaleZ,
            data_integration.scan3dCoordinateOffsetZ,
        )
        if camera_plane_alignments:
            data_integration.set("cameraPlaneAlignments",
                                 camera_plane_alignments)
            logger.info(
                f"aligned camera 3D planes: coil={data_integration.coilId}, "
                f"surface={data_integration.surface}, "
                f"adjustments={camera_plane_alignments}"
            )
        horizontal_projection_list = tool.get_horizontal_projection_list([data["MASK"] for data in datas])
        cross_points = tool.find_cross_points(horizontal_projection_list)
        data_integration.set_cross_points(cross_points)

        min_height = min([data["2D"].shape[0] for data in datas])
        for index in range(len(datas)):
            datas[index]['2D'] = datas[index]['2D'][:min_height, :]
            datas[index]['MASK'] = datas[index]['MASK'][:min_height, :]
            datas[index]['3D'] = datas[index]['3D'][:min_height, :]
            if index > 0:
                l_p = cross_points[index - 1][0]
                r_p = cross_points[index - 1][1]
                w = datas[index - 1]['2D'].shape[1]
                if l_p > serverConfigProperty.max_clip_mun:
                    l_p = 0
                if self.direction == "L":
                    datas[index - 1]['2D'] = datas[index - 1]['2D'][:, :w - l_p]
                    datas[index - 1]['MASK'] = datas[index - 1]['MASK'][:, :w - l_p]
                    datas[index - 1]['3D'] = datas[index - 1]['3D'][:, :w - l_p]

                if self.direction == "R":
                    datas[index]['2D'] = datas[index]['2D'][:, r_p:]
                    datas[index]['MASK'] = datas[index]['MASK'][:, r_p:]
                    datas[index]['3D'] = datas[index]['3D'][:, r_p:]

        leveling_2d(datas)
        join_image = np.hstack([data["2D"] for data in datas])
        join_mask_image = np.hstack([data["MASK"] for data in datas])

        # Camera depths are first converted to the reference Z calibration, then
        # edge-aligned so adjacent camera seams stay on the same plane.
        npy_data = tool.hstack_3d([data["3D"] for data in datas],
                                  join_mask_image=join_mask_image)

        if self.rotate == 90 or data_integration.surface == "S":
            join_image = np.rot90(join_image, 1)
            join_mask_image = np.rot90(join_mask_image, 1)
            npy_data = np.rot90(npy_data, 1)
            join_image = cv2.flip(join_image, 1)
            join_mask_image = cv2.flip(join_mask_image, 1)
            npy_data = cv2.flip(npy_data, 1)

        if self.rotate == -90 or data_integration.surface == "L":
            join_image = np.rot90(join_image, -1)
            join_mask_image = np.rot90(join_mask_image, -1)
            npy_data = np.rot90(npy_data, -1)

        box = tool.crop_black_border(join_mask_image)
        x, y, w, h = box
        data_integration.set("rotate", self.rotate)
        data_integration.set("crop_box", box)
        join_mask_image = join_mask_image[y:y + h, x:x + w]
        join_image = join_image[y:y + h, x:x + w]
        npy_data = npy_data[y:y + h, x:x + w]
        if np.max(join_mask_image.shape) < control.minMaskDetectErrorSize:
            self.raise_error(f"算法错误： mask shape: {join_mask_image.shape} 小于 {control.minMaskDetectErrorSize}")
        data_integration.joinImage = join_image

        data_integration.npy_image = join_image
        data_integration.pil_image = Image.fromarray(join_image)

        data_integration.npy_mask = join_mask_image
        data_integration.pil_mask = Image.fromarray(join_mask_image)
        data_integration.set_npy_data(npy_data)

        return join_image, join_mask_image, npy_data

    @DetectionSpeedRecord.timing_decorator("图像保持")
    def sync_save(self,data_integration):
        return asyncio.run(self.save_all_data(data_integration))

    async def save_all_data(self, data_integration: DataIntegration):
        await self.save_image(data_integration)
        await self.save3_d(data_integration)
        await self.save_json(data_integration)

    def run(self):
        # 拼接后的主函数
        self.imageSaver = ImageSaver(self.managerQueue, self.loggerProcess)
        self.d3Saver = D3Saver(self.managerQueue, self.loggerProcess)
        self.dataFolderList = []
        for folderConfig in self.config["folderList"]:
            fd_dt = [folderConfig, self.config["saveFolder"], self.config["direction"]]
            self.dataFolderList.append(DataFolder(fd_dt, self.loggerProcess.get_logger()))
        while self._running:
            coil_id = self.producer.get()
            if coil_id is None:
                break
            data_integration = DataIntegration(coil_id, self.saveFolder, self.direction, self.key)
            try:
                logger.info(f"ImageMosaic {self.key} {data_integration.coilId}")
                total_start = time.perf_counter()
                get_data_start = time.perf_counter()
                self.__getAllData__(data_integration)  # 获取全部的拼接数据
                get_data_s = time.perf_counter() - get_data_start
                original_start = time.perf_counter()
                data_integration.set_original_data(data_integration.datas)
                original_s = time.perf_counter() - original_start
                # 裁剪 2D 3D MASK
                stitch_start = time.perf_counter()
                self.__stitching__(data_integration)
                stitch_s = time.perf_counter() - stitch_start
                data_integration.currentSecondaryCoil = self.currentSecondaryCoil
                save_start = time.perf_counter()
                self.sync_save(data_integration)
                save_s = time.perf_counter() - save_start
                # Thread(target=self.sync_save, args=(data_integration,)).start()
                # self.sync_save(data_integration)
                # AlarmDetection.detection(data_integration)

                # AlarmDetection.detectionAll(data_integration)

                commit_start = time.perf_counter()
                data_integration.commit()
                commit_s = time.perf_counter() - commit_start
                logger.info(
                    f"perf ImageMosaic coil={coil_id} surface={self.key} get_data_s={get_data_s:.3f} "
                    f"set_original_s={original_s:.3f} stitch_s={stitch_s:.3f} save_s={save_s:.3f} "
                    f"commit_s={commit_s:.3f} total_s={time.perf_counter() - total_start:.3f}"
                )
            except ServerDetectionException as e:
                error_message = traceback.format_exc()
                logging.error(f"Error in ImageMosaic {data_integration.coilId}: {error_message}")
                data_integration.add_server_detection_error(e)
                logger.warning("ImageMosaic recovered after detection error, continue server")
            except Exception as e:
                error_message = traceback.format_exc()
                # raise e
                logging.error(f"Error in ImageMosaic {data_integration.coilId}: {error_message}")
                if isLoc and Globs.control.debug_raise:
                    six.reraise(Exception, e)

            finally:
                self.consumer.put(data_integration)

    def stop(self):
        self._running = False
        # 退出 run 循环
        self.producer.put(None)
        # 停止工作进程/线程
        if self.imageSaver:
            self.imageSaver.join()
        if self.d3Saver:
            self.d3Saver.join()

    def get_data(self):
        return self.consumer.get()

    def has_folder(self, coil_id):
        """
        文件夹是否存在
        Args:
            coil_id:

        Returns:

        """
        for folderConfig in self.config["folderList"]:
            if not DataFolder.static_has_data(Path(folderConfig["source"]), coil_id):
                return False
        return True

    def check_detection_end(self, coil_id):
        for folderConfig in self.config["folderList"]:
            if not DataFolder.static_check_detection_end(Path(folderConfig["source"]), coil_id):
                return False
        return True

    def has_data(self, coil_id):
        return self.has_folder(coil_id)
