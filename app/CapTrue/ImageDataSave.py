import json
import os
from collections import deque
from pathlib import Path
from queue import Full, Queue
from threading import Thread

from PIL import Image

from CONFIG import capTureConfig
from CoilDataBase.Coil import add_obj
from CoilDataBase.models.SecondaryCoil import SecondaryCoil
from CoilDataBase.models.CapTrueLogItem import CapTrueLogItem
from CoilDataBase.storage_policy import should_store_capture_raw_files
from Base.tools.compressed_storage import save_compressed_image, save_compressed_numpy
from ImageBuffer import SickBuffer, DaHengBuffer
from Camera import SickCamera
from Log import logger


CAPTURE_SAVE_QUEUE_PUT_TIMEOUT = float(os.getenv("LG3D_CAPTURE_SAVE_QUEUE_PUT_TIMEOUT", "2.0"))
CAPTURE_MAX_SAVE_INDEX = int(os.getenv("LG3D_CAPTURE_MAX_SAVE_INDEX", "20"))


class ImageDataSave(Thread):
    def __init__(self, save_folder):
        super().__init__()
        self.saveFolder = Path(save_folder)
        self.name = self.saveFolder.name
        self.save_index = 0
        self.save_index_2d = 0
        self.queue = Queue(maxsize=30)
        self.running = True
        self.daemon = True
        self.camera:SickCamera|None = None
        self.created_files = deque(maxlen=200)
        self.dropped_buffers = 0
        self.start()

    def set_camera(self, camera):
        self.camera = camera

    def trigger_init(self, coil:SecondaryCoil):
        logger.debug("triggerInit %s", coil)
        image2_d_folder = self.saveFolder / str(coil.Id)/ "2d"
        if image2_d_folder.exists():
            files = image2_d_folder.glob("*")
            self.save_index = len(list(files))

    def trigger_in(self, coil):
        logger.debug("triggerIn %s", coil)
        self.save_index = 0
        self.save_index_2d = 0

    def trigger_out(self, coil):
        logger.debug("triggerOut %s", coil)

    def stop(self):
        self.running = False
        try:
            self.queue.put(None, timeout=0.2)
        except Full:
            logger.debug("capture save queue full while stopping: camera=%s", self.name)

    def _queue_size(self):
        try:
            return self.queue.qsize()
        except NotImplementedError:
            return None

    def _queue_buffer(self, buffer) -> bool:
        try:
            self.queue.put(buffer, timeout=CAPTURE_SAVE_QUEUE_PUT_TIMEOUT)
            return True
        except Full:
            self.dropped_buffers += 1
            logger.error(
                "capture save queue full, drop buffer: camera=%s coil_id=%s index=%s type=%s dropped=%s queue_size=%s",
                self.name,
                getattr(buffer, "coilId", ""),
                getattr(buffer, "save_index", ""),
                type(buffer).__name__,
                self.dropped_buffers,
                self._queue_size(),
            )
            return False

    def put(self, buffer: SickBuffer | DaHengBuffer):
        if isinstance(buffer, SickBuffer):
            buffer.save_index = self.save_index
            if self.save_index < CAPTURE_MAX_SAVE_INDEX:
                self._queue_buffer(buffer)
            else:
                logger.error("<save_index out >%s <max %s>", self.save_index, CAPTURE_MAX_SAVE_INDEX)
            self.save_index += 1
        elif isinstance(buffer, DaHengBuffer):
            buffer.save_index = self.save_index_2d
            if self.save_index_2d < CAPTURE_MAX_SAVE_INDEX:
                self._queue_buffer(buffer)
            else:
                logger.error("<save_index_2d out >%s <max %s>", self.save_index_2d, CAPTURE_MAX_SAVE_INDEX)
            self.save_index_2d += 1

    def save_camera_config(self, buffer):
        saveFile = self.saveFolder / buffer.coilId / "camera_config.json"
        saveFile.parent.mkdir(parents=True, exist_ok=True)
        with saveFile.open("w", encoding="utf-8") as f:
            json.dump(self.camera.globCameraInfo, f, indent=4, ensure_ascii=False, sort_keys = True)
        self._record_created_file(saveFile, "camera_config", buffer)

    def _record_created_file(self, save_file, file_type, buffer):
        self.created_files.append({
            "path": str(save_file),
            "type": file_type,
            "coilId": str(getattr(buffer, "coilId", "")),
            "index": int(getattr(buffer, "save_index", 0)),
            "cameraName": self.name,
        })

    def get_created_files(self, clear=False):
        files = list(self.created_files)
        if clear:
            self.created_files.clear()
        return files

    def save_json(self, buffer):
        if not should_store_capture_raw_files():
            return
        buffer: SickBuffer
        buffer.data2D_mean = float(buffer.data2D.mean())
        buffer.data3D_mean = float(buffer.data3D.mean())
        save_file = self.saveFolder / buffer.coilId / "json" / f"{buffer.save_index}.json"
        save_file.parent.mkdir(parents=True, exist_ok=True)
        with save_file.open("w", encoding="utf-8") as f:
            json.dump(buffer.get_json(), f, indent=4, ensure_ascii=False, sort_keys=True)
        self._record_created_file(save_file, "json", buffer)

    def save3_d(self, buffer):
        if not should_store_capture_raw_files():
            return
        buffer: SickBuffer
        save_file = self.saveFolder / buffer.coilId / "3d" / f"{buffer.save_index}.npz"
        save_compressed_numpy(buffer.data3D, save_file)
        self._record_created_file(save_file, "3d", buffer)

    def _save_array_image(self, image_array, save_file, file_type, buffer):
        image = Image.fromarray(image_array)
        try:
            save_compressed_image(image, save_file)
        finally:
            image.close()
        self._record_created_file(save_file, file_type, buffer)

    def save_area_2d(self, buffer):
        buffer: DaHengBuffer
        if buffer.if_save_index():
            save_file = self.saveFolder / buffer.coilId / "area" / f"{buffer.save_index}.jpg"
            self._save_array_image(buffer.data2D, save_file, "area", buffer)

    def save2_d(self, buffer):
        save_file = self.saveFolder / buffer.coilId / "2d" / f"{buffer.save_index}.jpg"
        self._save_array_image(buffer.data2D, save_file, "2d", buffer)

    def save_area_2d_(self,buffer):
        if buffer.area_cap is not None:
            save_file = self.saveFolder / buffer.coilId / "2d" / f"{buffer.save_index}.jpg"
            self._save_array_image(buffer.area_cap, save_file, "2d_area", buffer)

    def save_database(self, buffer):
        if getattr(buffer, "coilData", None) is None:
            logger.debug(
                "skip capture database log without coil object: camera=%s coil_id=%s index=%s",
                self.name,
                buffer.coilId,
                buffer.save_index,
            )
            return None
        try:
            return add_obj(CapTrueLogItem(
                secondaryCoilId=buffer.coilId,
                cameraId =capTureConfig.index(self.name),
                cameraName=self.name,
                imageIndex=buffer.save_index
            ))
        except Exception as e:
            logger.exception(
                "save capture database log failed: camera=%s coil_id=%s index=%s error=%s",
                self.name,
                buffer.coilId,
                buffer.save_index,
                e,
            )

    def save(self, buffer):
        if isinstance(buffer, SickBuffer):
            logger.debug("save folder: %s index: %s", self.saveFolder / buffer.coilId, buffer.save_index)
            self.save_database(buffer)
            buffer: SickBuffer
            try:
                self.save_json(buffer)
            except Exception as e:
                logger.exception("save capture json failed: camera=%s coil_id=%s index=%s error=%s",
                                 self.name, buffer.coilId, buffer.save_index, e)
            try:
                self.save3_d(buffer)
            except Exception as e:
                logger.exception("save 3D data failed: camera=%s coil_id=%s index=%s error=%s",
                                 self.name, buffer.coilId, buffer.save_index, e)
            try:
                self.save2_d(buffer)
            except Exception as e:
                logger.exception("save 2D image failed: camera=%s coil_id=%s index=%s error=%s",
                                 self.name, buffer.coilId, buffer.save_index, e)
            if buffer.save_index == 0:
                if self.camera:
                    try:
                        self.save_camera_config(buffer)
                    except Exception as e:
                        logger.exception("save camera config failed: camera=%s coil_id=%s error=%s",
                                         self.name, buffer.coilId, e)
        if isinstance(buffer, DaHengBuffer):
            logger.debug("save folder: %s index: %s", self.saveFolder / buffer.coilId, buffer.save_index)
            buffer: DaHengBuffer
            try:
                self.save_area_2d(buffer)
            except Exception as e:
                logger.exception("save 2D AREA image failed: camera=%s coil_id=%s index=%s error=%s",
                                 self.name, buffer.coilId, buffer.save_index, e)

    def run(self):
        while self.running:
            data = self.queue.get()
            if data is None:
                break
            try:
                self.save(data)
            except Exception as e:
                logger.exception(
                    "capture save worker failed: camera=%s buffer_type=%s coil_id=%s index=%s error=%s",
                    self.name,
                    type(data).__name__,
                    getattr(data, "coilId", ""),
                    getattr(data, "save_index", ""),
                    e,
                )
