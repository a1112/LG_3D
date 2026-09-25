import asyncio
import os
import threading
import time

from pathlib import Path
from queue import Empty, Full

import cv2
import numpy as np
from PIL import Image
from Base.CONFIG import isLoc, serverConfigProperty
from SplicingService.DataFolderLog import DataFolderLog
from SplicingService.capture_paths import (
    LINE_SCAN_TWO_D_DIR_NAMES,
    THREE_D_DIR_NAMES,
    capture_complete,
    resolve_capture_dir,
    select_capture_frame_sequence,
    sorted_indexed_files,
)
from Base.tools.compressed_storage import load_json_file
from Base.tools.Glob import cmdThread

from Base.tools import tool

from Base.utils import Log
from Base import Globs
from algorithm_runtime.runtime_heartbeat import runtime_heartbeat

logger = Log.logger
MIN_VALID_3D_FRAME_RATIO = float(
    os.getenv("LG3D_MIN_VALID_3D_FRAME_RATIO", "0.02"))
MIN_VALID_3D_FRAME_POINTS = int(
    os.getenv("LG3D_MIN_VALID_3D_FRAME_POINTS", "10000"))
MIN_VALID_3D_FRAMES = int(os.getenv("LG3D_MIN_VALID_3D_FRAMES", "2"))


def _queue_timeout(name: str, default: float) -> float:
    try:
        return max(float(os.getenv(name, str(default))), 0.1)
    except ValueError:
        logger.warning("invalid %s, use %s", name, default)
        return default


DATA_FOLDER_QUEUE_TIMEOUT = _queue_timeout("LG3D_DATA_FOLDER_QUEUE_TIMEOUT", 5.0)
DATA_FOLDER_RESULT_TIMEOUT = _queue_timeout("LG3D_DATA_FOLDER_RESULT_TIMEOUT", 60.0)
_shared_coil_area_model = None
_shared_coil_area_model_lock = threading.Lock()


def _get_shared_coil_area_model():
    """Load one area model per process instead of one per camera thread."""
    global _shared_coil_area_model
    if _shared_coil_area_model is not None:
        return _shared_coil_area_model
    with _shared_coil_area_model_lock:
        if _shared_coil_area_model is None:
            from Base.alg.CoilMaskModel import CoilAreaModel
            _shared_coil_area_model = CoilAreaModel()
    return _shared_coil_area_model


class DataFolder(Globs.control.BaseDataFolder):

    def __init__(self, fd, logger_process):
        super().__init__()
        self.daemon = True
        self._stop_event = threading.Event()
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
        return capture_complete(source,
                                coil_id,
                                dir_names=LINE_SCAN_TWO_D_DIR_NAMES)

    def get_data(self, timeout=None, expected_coil_id=None):
        if timeout is None:
            timeout = DATA_FOLDER_RESULT_TIMEOUT
        deadline = time.monotonic() + max(float(timeout), 0.0)
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(
                    f"DataFolder result timeout camera={self.folderName} "
                    f"coil={expected_coil_id} timeout={timeout}s")
            try:
                result = self.consumer.get(timeout=min(remaining, 0.5))
            except Empty:
                if self._stop_event.is_set():
                    raise RuntimeError(
                        f"DataFolder stopped camera={self.folderName}")
                continue
            actual_coil_id = result.get("coil_id") if isinstance(result, dict) else None
            if (expected_coil_id is None
                    or str(actual_coil_id) == str(expected_coil_id)):
                return result
            logger.warning(
                "drop stale DataFolder result: camera=%s expected=%s actual=%s",
                self.folderName,
                expected_coil_id,
                actual_coil_id,
            )

    def set_coil_id(self, coil_id, stems=None):
        if self._stop_event.is_set():
            return False
        work_item = coil_id if stems is None else {
            "coil_id": coil_id,
            "stems": list(stems),
        }
        try:
            self.producer.put(work_item, timeout=DATA_FOLDER_QUEUE_TIMEOUT)
            return True
        except Full:
            logger.error(
                "DataFolder producer queue full: camera=%s coil=%s",
                self.folderName,
                coil_id,
            )
            return False

    def _publish_result(self, data) -> None:
        try:
            self.consumer.put(data, timeout=DATA_FOLDER_QUEUE_TIMEOUT)
            return
        except Full:
            pass

        try:
            stale = self.consumer.get_nowait()
            logger.warning(
                "discard blocked DataFolder result: camera=%s stale_coil=%s new_coil=%s",
                self.folderName,
                stale.get("coil_id") if isinstance(stale, dict) else None,
                data.get("coil_id") if isinstance(data, dict) else None,
            )
        except Empty:
            pass
        try:
            self.consumer.put(data, timeout=DATA_FOLDER_QUEUE_TIMEOUT)
        except Full:
            logger.error(
                "DataFolder result queue remained full: camera=%s coil=%s",
                self.folderName,
                data.get("coil_id") if isinstance(data, dict) else None,
            )

    def mk_link(self, coil_id):
        coil_id = str(coil_id)
        link_folder = self.saveFolder / coil_id / "link"
        link_folder.mkdir(parents=True, exist_ok=True)
        target = self.source / coil_id
        link_path = link_folder / self.folderName
        if link_path.exists() or link_path.is_symlink():
            return True
        try:
            link_path.symlink_to(target, target_is_directory=True)
            logger.info("created capture source link: %s -> %s", link_path,
                        target)
            return True
        except FileExistsError:
            return True
        except OSError as e:
            logger.warning(
                "direct capture source link creation failed, queue mklink: "
                "link=%s target=%s error=%s",
                link_path,
                target,
                e,
            )
        cmd = fr'mklink /D "{link_path}" "{target}"'
        return cmdThread.put(cmd)

    def _load_json_frames(self, coil_id):
        source_json = self.source / coil_id / "json"
        source_json_list = sorted_indexed_files(source_json, ("*.json", ))
        frame_records = [(path, load_json_file(path))
                         for path in source_json_list]
        selected_records = select_capture_frame_sequence(frame_records)
        if len(selected_records) != len(frame_records):
            selected_paths = {path for path, _ in selected_records}
            logger.warning(
                "discard non-contiguous capture frames: coil=%s, camera=%s, discarded=%s, selected=%s",
                coil_id,
                self.folderName,
                [
                    self._frame_stem(path)
                    for path, _ in frame_records if path not in selected_paths
                ],
                [self._frame_stem(path) for path, _ in selected_records],
            )
        source_json_list = [path for path, _ in selected_records]
        json_datas = [data for _, data in selected_records]
        stem_list = [self._frame_stem(data) for data in source_json_list]
        return json_datas, stem_list

    def load_json(self, coil_id, forced_stems=None):
        json_datas, stem_list = self._load_json_frames(coil_id)
        if forced_stems is not None:
            metadata_by_stem = dict(zip(stem_list, json_datas))
            stem_list = [
                None if stem is None else str(stem) for stem in forced_stems
            ]
            json_datas = [
                metadata_by_stem.get(stem, {}) if stem is not None else {}
                for stem in stem_list
            ]
            logger.warning(
                "use aligned capture frames: coil=%s, camera=%s, stems=%s, missing_slots=%s",
                coil_id,
                self.folderName,
                stem_list,
                [
                    index
                    for index, stem in enumerate(stem_list) if stem is None
                ],
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
                return data["array"] if "array" in data.files else data[
                    data.files[0]]
        return np.load(path)

    def filter_empty_3d_frames(self, coil_id, json_datas, stem_list):
        source3_d = resolve_capture_dir(self.source, coil_id,
                                        THREE_D_DIR_NAMES)
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
                    "skip unreadable 3D frame: coil=%s, camera=%s, stem=%s, error=%s",
                    coil_id,
                    self.folderName,
                    stem,
                    e,
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
                "filtered empty 3D frames: coil=%s, camera=%s, rejected=%s, kept=%s",
                coil_id,
                self.folderName,
                rejected,
                kept_stems,
            )
        if len(kept_stems) < MIN_VALID_3D_FRAMES:
            logger.warning(
                "too few valid 3D frames after filtering, keep original frames: "
                "coil=%s, camera=%s, kept=%s, original=%s",
                coil_id,
                self.folderName,
                kept_stems,
                stem_list,
            )
            return json_datas, stem_list
        return kept_json_datas, kept_stems

    def get_valid_3d_stems(self, coil_id):
        json_datas, stem_list = self._load_json_frames(coil_id)
        _, kept_stems = self.filter_empty_3d_frames(coil_id, json_datas,
                                                    stem_list)
        return kept_stems

    def get_capture_stems(self, coil_id):
        _, stem_list = self._load_json_frames(coil_id)
        return stem_list

    def get_capture_frames(self, coil_id):
        json_datas, stem_list = self._load_json_frames(coil_id)
        return list(zip(stem_list, json_datas))

    async def load2_d(self, coil_id, stem_list):
        source2_d = resolve_capture_dir(self.source, coil_id,
                                        LINE_SCAN_TWO_D_DIR_NAMES)

        async def read_2d(stem):
            """异步读取 BMP 文件并返回图像数据"""
            # 异步模拟读取
            if stem is None:
                return None
            image_f_ = source2_d / (stem + ".bmp")
            if not image_f_.exists():
                image_f_ = source2_d / (stem + ".jpg")
            with Image.open(image_f_) as image_:
                return np.array(image_)

        images = await asyncio.gather(*[read_2d(stem) for stem in stem_list])
        template = next((image for image in images if image is not None), None)
        if template is None:
            raise FileNotFoundError(
                f"no 2D capture frames: coil={coil_id} camera={self.folderName}"
            )
        frame_validity = np.vstack([
            np.zeros(template.shape[:2], dtype=np.uint8)
            if image is None else np.full(image.shape[:2], 255, dtype=np.uint8)
            for image in images
        ])
        source_images = images
        images = [
            np.zeros_like(template) if image is None else image
            for image in source_images
        ]
        join_image = np.vstack(images)
        mask = np.zeros(join_image.shape[:2], dtype=np.uint8)
        row_offset = 0
        segment_start = None
        for source_image, image in zip(source_images, images):
            if source_image is None:
                if segment_start is not None:
                    _, segment_mask = tool.get_foreground(
                        join_image[segment_start:row_offset], self.direction,
                        self.folderName)
                    mask[segment_start:row_offset] = segment_mask
                    segment_start = None
            elif segment_start is None:
                segment_start = row_offset
            row_offset += image.shape[0]
        if segment_start is not None:
            _, segment_mask = tool.get_foreground(
                join_image[segment_start:row_offset], self.direction,
                self.folderName)
            mask[segment_start:row_offset] = segment_mask
        rec = tool.crop_max_image_black_edges(self.folderName, mask,
                                              [self.cropLeft, self.cropRight])
        return join_image, mask, rec, frame_validity

    @staticmethod
    def _clamp_rec(rec, image_shape):
        image_h, image_w = image_shape[:2]
        if image_h <= 0 or image_w <= 0:
            return [0, 0, 0, 0]
        try:
            x, y, w, h = [int(value) for value in rec]
        except (TypeError, ValueError):
            return [0, 0, image_w, image_h]
        x = min(max(x, 0), image_w - 1)
        y = min(max(y, 0), image_h - 1)
        right = min(max(x + max(w, 1), x + 1), image_w)
        bottom = min(max(y + max(h, 1), y + 1), image_h)
        return [x, y, right - x, bottom - y]

    @staticmethod
    def _crop_by_rec(image, rec):
        x, y, w, h = rec
        return image[y:y + h, x:x + w]

    @classmethod
    def _crop_aligned_by_2d_rec(cls, image2_d, image_mask, data3_d, rec):
        crop_rec = cls._clamp_rec(rec, image2_d.shape)
        return (
            crop_rec,
            cls._crop_by_rec(image2_d, crop_rec),
            cls._crop_by_rec(image_mask, crop_rec),
            cls._crop_by_rec(data3_d, crop_rec),
        )

    async def load3_d(self, coil_id, stem_list, json_data_list):
        source3_d = resolve_capture_dir(self.source, coil_id,
                                        THREE_D_DIR_NAMES)

        async def read_3d(stem):
            """异步读取 BMP 文件并返回图像数据"""
            # 异步模拟读取
            if stem is None:
                return None
            npy_f_ = source3_d / (stem + ".npy")
            if not npy_f_.exists():
                npy_f_ = source3_d / (stem + ".npz")
                with np.load(npy_f_) as archive:
                    return archive["array"].copy()
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
        arrays = await asyncio.gather(*[read_3d(stem) for stem in stem_list])
        template = next((array for array in arrays if array is not None), None)
        if template is None:
            raise FileNotFoundError(
                f"no 3D capture frames: coil={coil_id} camera={self.folderName}"
            )
        arrays = [
            np.zeros_like(template) if array is None else array
            for array in arrays
        ]
        return np.vstack(arrays)

    def has_data(self, coil_id):
        return self.static_has_data(self.source, coil_id)

    @staticmethod
    def static_has_data(source, coil_id):
        source = Path(source)
        exists = (source / coil_id).exists()
        if not exists:
            logger.error("DataFolder %s does not exist. %s", coil_id,
                         source / coil_id)
        return exists

    def run(self):
        self.imageMosaicList = []
        self.saveMask = serverConfigProperty.saveJoinMask
        if self.saveMask:
            self.saveMaskFolder = self.source.parent / "SaveMask" / self.folderName
            self.saveMaskFolder.mkdir(parents=True, exist_ok=True)

        startup_activity = runtime_heartbeat.begin_activity(
            "3d_camera_model_initialization",
            self.folderName,
        )
        try:
            self.coilAreaModel = _get_shared_coil_area_model()
        finally:
            runtime_heartbeat.end_activity(startup_activity)
        while not self._stop_event.is_set():
            try:
                work_item = self.producer.get(timeout=0.5)
            except Empty:
                continue
            if work_item is None:
                break
            forced_stems = None
            if isinstance(work_item, dict):
                coil_id = str(work_item.get("coil_id"))
                forced_stems = work_item.get("stems")
            else:
                coil_id = work_item
            total_start = time.perf_counter()
            data = {"camera": self.folderName, "coil_id": str(coil_id)}
            json_datas = None
            stem_list = None
            image2_d_full = None
            image_mask_full = None
            frame_validity_full = None
            data3_d_full = None
            image2_d = None
            image_mask = None
            frame_validity = None
            data3_d = None
            activity = runtime_heartbeat.begin_activity(
                f"3d_camera_{self.folderName}",
                coil_id,
            )
            # dataFolderLog = DataFolderLog(self)
            try:
                json_start = time.perf_counter()
                json_datas, stem_list = self.load_json(coil_id, forced_stems)
                json_s = time.perf_counter() - json_start
                load2d_start = time.perf_counter()
                image2_d_full, image_mask_full, rec, frame_validity_full = asyncio.run(
                    self.load2_d(coil_id, stem_list))
                load2d_s = time.perf_counter() - load2d_start
                load3d_start = time.perf_counter()
                data3_d_full = asyncio.run(
                    self.load3_d(coil_id, stem_list, json_datas))
                load3d_s = time.perf_counter() - load3d_start
                crop_rec, image2_d, image_mask, data3_d = self._crop_aligned_by_2d_rec(
                    image2_d_full,
                    image_mask_full,
                    data3_d_full,
                    rec,
                )
                frame_validity = self._crop_by_rec(frame_validity_full,
                                                   crop_rec)
                with Image.fromarray(image2_d) as steel_image:
                    steel_rec = self.coilAreaModel.getSteelRect(steel_image)
                data["json"] = json_datas
                data["frame_stems"] = stem_list
                data["missing_frame_slots"] = [
                    index for index, stem in enumerate(stem_list)
                    if stem is None
                ]
                data["2D"] = image2_d
                data["rec"] = steel_rec
                data["crop_rec"] = crop_rec
                data["image_crop_rec"] = rec
                data["MASK"] = image_mask
                data["VALIDITY"] = frame_validity

                post_start = time.perf_counter()
                data3_d = cv2.bitwise_and(data3_d, data3_d, mask=image_mask)
                data["3D"] = data3_d
                post_s = time.perf_counter() - post_start

                self.mk_link(coil_id)
                if self.saveMask:
                    with Image.fromarray(image2_d) as gray_image:
                        gray_image.save(self.saveMaskFolder /
                                        f"{coil_id}_{self.folderName}_GRAY.png")
                    with Image.fromarray(image_mask) as mask_image:
                        mask_image.save(self.saveMaskFolder /
                                        f"{coil_id}_{self.folderName}_MASK.png")

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
                    raise
            finally:
                logger.info("DataFolder %s end", coil_id)
                self._publish_result(data)
                runtime_heartbeat.end_activity(activity)
                # The queue owns `data` after publication. Clear every local
                # view/copy before this permanent worker blocks for the next
                # coil, otherwise one full camera dataset remains pinned.
                data = None
                work_item = None
                json_datas = None
                stem_list = None
                image2_d_full = None
                image_mask_full = None
                frame_validity_full = None
                data3_d_full = None
                image2_d = None
                image_mask = None
                frame_validity = None
                data3_d = None

    def stop(self):
        self._stop_event.set()
        try:
            self.producer.put_nowait(None)
        except Full:
            logger.warning("DataFolder stop queue full: camera=%s",
                           self.folderName)
