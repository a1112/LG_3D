import json
from collections import deque
from pathlib import Path
from threading import Thread
from queue import Queue

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


class ImageDataSave(Thread):
    def __init__(self, save_folder):
        super().__init__()
        self.saveFolder = Path(save_folder)
        self.name = self.saveFolder.name
        self.save_index = 0
        self.save_index_2d = 0
        self.queue = Queue(maxsize=30)
        self.running = True
        self.camera:SickCamera|None = None
        self.created_files = deque(maxlen=200)
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
        pass

    def put(self, buffer: SickBuffer | DaHengBuffer):
        if isinstance(buffer, SickBuffer):
            buffer.data2D_mean = buffer.data2D.mean()
            buffer.save_index = self.save_index
            if self.save_index<20:
                self.queue.put(buffer)
            else:
                logger.error("<save_index out >%s <max 20>", self.save_index)
            self.save_index += 1
        if isinstance(buffer, DaHengBuffer):
            buffer.save_index = self.save_index_2d
            if self.save_index_2d<20:
                self.queue.put(buffer)
            else:
                logger.error("<save_index_2d out >%s <max 20>", self.save_index_2d)
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

    def save_area_2d(self, buffer):
        buffer: DaHengBuffer
        if buffer.if_save_index():
                save_file = self.saveFolder / buffer.coilId / "area" / f"{buffer.save_index}.jpg"
                save_compressed_image(Image.fromarray(buffer.data2D), save_file)
                self._record_created_file(save_file, "area", buffer)

    def save2_d(self, buffer):
        save_file = self.saveFolder / buffer.coilId / "2d" / f"{buffer.save_index}.jpg"
        save_compressed_image(Image.fromarray(buffer.data2D), save_file)
        self._record_created_file(save_file, "2d", buffer)

    def save_area_2d_(self,buffer):
        if buffer.area_cap is not None:
            save_file = self.saveFolder / buffer.coilId / "2d" / f"{buffer.save_index}.jpg"
            save_compressed_image(Image.fromarray(buffer.area_cap), save_file)
            self._record_created_file(save_file, "2d_area", buffer)

    def save_database(self, buffer):
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
        if isinstance(buffer, SickBuffer ):
            logger.debug("save folder: %s index: %s", self.saveFolder / buffer.coilId, buffer.save_index)
            self.save_database(buffer)
            buffer: SickBuffer
            self.save_json(buffer)
            self.save3_d(buffer)
            try:
                self.save2_d(buffer)
            except Exception as e:
                logger.exception("save 2D image failed: camera=%s coil_id=%s index=%s error=%s",
                                 self.name, buffer.coilId, buffer.save_index, e)
            if buffer.save_index == 0:
                if self.camera:
                    self.save_camera_config(buffer)
        if isinstance(buffer, DaHengBuffer):
            logger.debug("save folder: %s index: %s", self.saveFolder / buffer.coilId, buffer.save_index)
            buffer: DaHengBuffer
            self.save_area_2d(buffer)

    def run(self):
        while self.running:
            data = self.queue.get()
            self.save(data)
