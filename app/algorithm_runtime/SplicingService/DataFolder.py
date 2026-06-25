import asyncio
import os
import time

from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from Base.CONFIG import isLoc, serverConfigProperty
from SplicingService.DataFolderLog import DataFolderLog
from SplicingService.capture_paths import (
    THREE_D_DIR_NAMES,
    TWO_D_DIR_NAMES,
    capture_complete,
    resolve_capture_dir,
    sorted_indexed_files,
)
from Base.tools.compressed_storage import load_json_file
from Base.tools.Glob import cmdThread

from Base.tools import tool

from Base.utils import Log
from Base import Globs

logger = Log.logger
MIN_VALID_3D_FRAME_RATIO = float(os.getenv("LG3D_MIN_VALID_3D_FRAME_RATIO", "0.02"))
MIN_VALID_3D_FRAME_POINTS = int(os.getenv("LG3D_MIN_VALID_3D_FRAME_POINTS", "10000"))
MIN_VALID_3D_FRAMES = int(os.getenv("LG3D_MIN_VALID_3D_FRAMES", "2"))


class DataFolder(Globs.control.BaseDataFolder):
    def __init__(self, fd, logger_process):
        super().__init__()
        self.coilAreaModel = None
        self.loggerProcess = logger_process
        self.saveMaskFolder = None
        self.saveMask = None
        self.imageMosaicList = None
        # fd = json.loads(fd)
        folder_config, save_folder, direction = fd
        self.direction = direction  # "L"
        self.saveFolder = Path(save_folder)
        self.folderConfig = folder_config
        self.source = Path(folder_config["source"])
        self.folderName = self.source.stem
        self.cropLeft = folder_config["cropLeft"]
        self.cropRight = folder_config["cropRight"]

        self.start()

    def check_detection_end(self, coil_id):
        return self.static_check_detection_end(self.source, coil_id)

    @staticmethod
    def static_check_detection_end(source, coil_id):
        return capture_complete(source, coil_id)

    def get_data(self):
        return self.consumer.get()

    def set_coil_id(self, coil_id, stems=None):
        if stems is None:
            self.producer.put(coil_id)
        else:
            self.producer.put({"coil_id": coil_id, "stems": list(stems)})

    def mk_link(self, coil_id):
        link_folder = self.saveFolder / coil_id / "link"
        link_folder.mkdir(parents=True, exist_ok=True)
        target = self.source / coil_id
        if (link_folder / self.folderName).exists():
            return
        # os.link(link_folder / self.folderName, self.source / coilId)
        cmd = fr'mklink /D "{link_folder / self.folderName}" "{target}"'
        cmdThread.put(cmd)

    def _load_json_frames(self, coil_id):
        source_json = self.source / coil_id / "json"
        source_json_list = sorted_indexed_files(source_json, ("*.json",))
        json_datas = []
        for i in range(len(source_json_list)):
            json_datas.append(load_json_file(source_json_list[i]))
        stem_list = [self._frame_stem(data) for data in source_json_list]
        timestamp_list = [data["timestamp"] // 10e7 for data in json_datas]
        if len(timestamp_list) < 2:
            return json_datas, stem_list
        timestamp_list_differ = []
        for i in range(len(timestamp_list) - 1):
            timestamp_list_differ.append(timestamp_list[i + 1] - timestamp_list[i])
        max_val = max(timestamp_list_differ)
        if max_val > 200:
            max_index = timestamp_list_differ.index(max_val)
            if max_index < len(timestamp_list_differ) - 5:
                stem_list = stem_list[max_index + 1:]
                json_datas = json_datas[max_index + 1:]
        return json_datas, stem_list

    def load_json(self, coil_id, forced_stems=None):
        json_datas, stem_list = self._load_json_frames(coil_id)
        if forced_stems is not None:
            forced_stems = {str(stem) for stem in forced_stems}
            filtered_pairs = [
                (json_data, stem)
                for json_data, stem in zip(json_datas, stem_list)
                if stem in forced_stems
            ]
            if filtered_pairs:
                json_datas = [json_data for json_data, _ in filtered_pairs]
                stem_list = [stem for _, stem in filtered_pairs]
            logger.warning(
                f"use common valid 3D frames: coil={coil_id}, camera={self.folderName}, "
                f"stems={stem_list}"
            )
            return json_datas, stem_list
        return self.filter_empty_3d_frames(coil_id, json_datas, stem_list)

    @staticmethod
    def _frame_stem(path):
        stem = path.name
        for suffix in reversed(path.suffixes):
            if stem.endswith(suffix):
                stem = stem[:-len(suffix)]
        return stem

    @staticmethod
    def _load_3d_array(path: Path):
        if path.suffix.lower() == ".npz":
            with np.load(path) as data:
                return data["array"] if "array" in data.files else data[data.files[0]]
        return np.load(path)

    def filter_empty_3d_frames(self, coil_id, json_datas, stem_list):
        source3_d = resolve_capture_dir(self.source, coil_id, THREE_D_DIR_NAMES)
        kept_json_datas = []
        kept_stems = []
        rejected = []
        for json_data, stem in zip(json_datas, stem_list):
            frame_path = source3_d / (stem + ".npy")
            if not frame_path.exists():
                frame_path = source3_d / (stem + ".npz")
            if not frame_path.exists():
                rejected.append(f"{stem}:missing")
                continue
            try:
                frame_data = self._load_3d_array(frame_path)
                valid_points = int(np.count_nonzero(frame_data))
                valid_ratio = valid_points / frame_data.size if frame_data.size else 0
            except Exception as e:
                logger.warning(
                    f"skip unreadable 3D frame: coil={coil_id}, camera={self.folderName}, "
                    f"stem={stem}, error={e}"
                )
                rejected.append(f"{stem}:error")
                continue
            if valid_points < MIN_VALID_3D_FRAME_POINTS or valid_ratio < MIN_VALID_3D_FRAME_RATIO:
                rejected.append(f"{stem}:{valid_points}/{valid_ratio:.4f}")
                continue
            kept_json_datas.append(json_data)
            kept_stems.append(stem)

        if rejected:
            logger.warning(
                f"filtered empty 3D frames: coil={coil_id}, camera={self.folderName}, "
                f"rejected={rejected}, kept={kept_stems}"
            )
        if len(kept_stems) < MIN_VALID_3D_FRAMES:
            logger.warning(
                f"too few valid 3D frames after filtering, keep original frames: "
                f"coil={coil_id}, camera={self.folderName}, kept={kept_stems}, original={stem_list}"
            )
            return json_datas, stem_list
        return kept_json_datas, kept_stems

    def get_valid_3d_stems(self, coil_id):
        json_datas, stem_list = self._load_json_frames(coil_id)
        _, kept_stems = self.filter_empty_3d_frames(coil_id, json_datas, stem_list)
        return kept_stems

    async def load2_d(self, coil_id, stem_list):
        source2_d = resolve_capture_dir(self.source, coil_id, TWO_D_DIR_NAMES)

        async def read_2d(stem):
            """异步读取 BMP 文件并返回图像数据"""
            # 异步模拟读取
            image_f_ = source2_d / (stem + ".bmp")
            if not image_f_.exists():
                image_f_ = source2_d / (stem + ".jpg")
            with Image.open(image_f_) as image_:
                return np.array(image_)
        images = await asyncio.gather(*[read_2d(stem) for stem in stem_list])
        join_image = np.vstack(images)
        # images = []
        # for stem in stem_list:
        #     image_f = source2_d / (stem + ".bmp")
        #     if not image_f.exists():
        #         image_f = source2_d / (stem + ".jpg")
        #     with Image.open(image_f) as image:
        #         images.append(np.array(image))
        cv_image, mask, rec = tool.auto_crop(self.folderName, join_image, [self.cropLeft, self.cropRight], self.direction)
        steel_rec = self.coilAreaModel.getSteelRect(Image.fromarray(cv_image))
        return cv_image, mask, rec, steel_rec

    async def load3_d(self, coil_id, rec, stem_list, json_data_list):
        source3_d = resolve_capture_dir(self.source, coil_id, THREE_D_DIR_NAMES)

        async def read_3d(stem):
            """异步读取 BMP 文件并返回图像数据"""
            # 异步模拟读取
            npy_f_ = source3_d / (stem + ".npy")
            if not npy_f_.exists():
                npy_f_ = source3_d / (stem + ".npz")
                return np.load(npy_f_)["array"]
            else:
                return np.load(npy_f_)


        # npy_list = []
        # for stem, jsData in zip(stem_list, json_data_list):
        #     npy_f = source3_d / (stem + ".npy")
        #     if not npy_f.exists():
        #         npz_f = source3_d / (stem + ".npz")
        #         npy = np.load(npz_f)["array"]
        #     else:
        #         npy = np.load(npy_f)
        #     npy_list.append(npy)
        # npy = np.vstack(npy_list)
        npy = np.vstack( await asyncio.gather(*[read_3d(stem) for stem in stem_list]))
        if rec:
            npy = npy[:, rec[0]:rec[0] + rec[2]]
        return npy

    def has_data(self, coil_id):
        return self.static_has_data(self.source, coil_id)

    @staticmethod
    def static_has_data(source, coil_id):
        source = Path(source)
        exists = (source / coil_id).exists()
        if not exists:
            logger.error("DataFolder %s does not exist. %s", coil_id, source / coil_id)
        return exists

    def run(self):
        self.imageMosaicList = []
        self.saveMask = serverConfigProperty.saveJoinMask
        if self.saveMask:
            self.saveMaskFolder = self.source.parent / "SaveMask" / self.folderName
            self.saveMaskFolder.mkdir(parents=True, exist_ok=True)

        from Base.alg.CoilMaskModel import CoilAreaModel
        self.coilAreaModel = CoilAreaModel()
        while True:
            work_item = self.producer.get()
            forced_stems = None
            if isinstance(work_item, dict):
                coil_id = str(work_item.get("coil_id"))
                forced_stems = work_item.get("stems")
            else:
                coil_id = work_item
            total_start = time.perf_counter()
            data = {"camera": self.folderName}
            # dataFolderLog = DataFolderLog(self)
            try:
                json_start = time.perf_counter()
                json_datas, stem_list = self.load_json(coil_id, forced_stems)
                json_s = time.perf_counter() - json_start
                load2d_start = time.perf_counter()
                image2_d, image_mask, rec, steel_rec = asyncio.run(self.load2_d(coil_id, stem_list))
                load2d_s = time.perf_counter() - load2d_start
                load3d_start = time.perf_counter()
                data3_d =  asyncio.run(self.load3_d(coil_id, rec, stem_list, json_datas))
                load3d_s = time.perf_counter() - load3d_start
                data["json"] = json_datas
                data["2D"] = image2_d
                data["rec"] = steel_rec
                data["crop_rec"] = rec
                data["MASK"] = image_mask

                post_start = time.perf_counter()
                data3_d = cv2.bitwise_and(data3_d, data3_d, mask=image_mask)
                data["3D"] = data3_d
                post_s = time.perf_counter() - post_start

                self.mk_link(coil_id)
                if self.saveMask:
                    Image.fromarray(image2_d).save(self.saveMaskFolder / f"{coil_id}_{self.folderName}_GRAY.png")
                    Image.fromarray(image_mask).save(self.saveMaskFolder / f"{coil_id}_{self.folderName}_MASK.png")

                # 显示图像
                logger.info(
                    "perf DataFolder coil=%s camera=%s frames=%s json_s=%.3f load2d_s=%.3f "
                    "load3d_s=%.3f post_s=%.3f total_s=%.3f",
                    coil_id,
                    self.folderName,
                    len(stem_list),
                    json_s,
                    load2d_s,
                    load3d_s,
                    post_s,
                    time.perf_counter() - total_start,
                )
            except Exception as e:
                logger.error("Error in DataFolder %s: %s", coil_id, e)
                if isLoc and Globs.control.debug_raise:
                    raise e
            finally:
                logger.info("DataFolder %s end", coil_id)
                self.consumer.put(data)
