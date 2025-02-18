import json
from pathlib import Path
from threading import Thread
from queue import Queue

import numpy as np
from PIL import Image

from CONFIG import capTureConfig
from CoilDataBase.Coil import add_obj
from CoilDataBase.models.SecondaryCoil import SecondaryCoil
from CoilDataBase.models.CapTrueLogItem import CapTrueLogItem
from ImageBuffer import SickBuffer
from Camera import SickCamera
from Log import logger


class ImageDataSave(Thread):
    def __init__(self, save_folder):
        super().__init__()
        self.saveFolder = Path(save_folder)
        self.name = self.saveFolder.name
        self.save_index = 0
        self.queue = Queue()
        self.running = True
        self.camera:SickCamera|None = None
        self.start()

    def set_camera(self, camera):
        self.camera = camera

    def trigger_init(self, coil:SecondaryCoil):
        logger.debug(f"triggerInit {coil}")
        image2_d_folder = self.saveFolder / str(coil.Id)/ "2d"
        if image2_d_folder.exists():
            files = image2_d_folder.glob("*")
            self.save_index = len(list(files))

    def trigger_in(self, coil):
        logger.debug(f"triggerIn {coil}")
        self.save_index = 0

    def trigger_out(self, coil):
        pass

    def put(self, buffer: SickBuffer):
        buffer.data2D_mean = buffer.data2D.mean()
        buffer.save_index = self.save_index
        self.queue.put(buffer)
        self.save_index += 1

    def save_camera_config(self, buffer):
        saveFile = self.saveFolder / buffer.coilId / "camera_config.json"
        saveFile.parent.mkdir(parents=True, exist_ok=True)
        with saveFile.open("w", encoding="utf-8") as f:
            json.dump(self.camera.globCameraInfo, f,indent=4,ensure_ascii=False,sort_keys=True)

    def save_json(self, buffer):
        buffer: SickBuffer
        save_file = self.saveFolder / buffer.coilId / "json" / f"{buffer.save_index}.json"
        save_file.parent.mkdir(parents=True, exist_ok=True)
        with save_file.open("w", encoding="utf-8") as f:
            json.dump(buffer.get_json(), f,indent=4,ensure_ascii=False,sort_keys=True)

    def save3_d(self, buffer):
        buffer: SickBuffer
        save_file = self.saveFolder / buffer.coilId / "3d" / f"{buffer.save_index}.npy"
        save_file.parent.mkdir(parents=True, exist_ok=True)
        np.save(str(save_file), buffer.data3D)

    def save2_d(self, buffer):
        save_file = self.saveFolder / buffer.coilId / "2d" / f"{buffer.save_index}.bmp"
        save_file.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(buffer.data2D).save(str(save_file))

    def save_area_2d(self,buffer):
        save_file = self.saveFolder / buffer.coilId / "area" / f"{buffer.save_index}.bmp"
        save_file.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(buffer.area_cap).save(str(save_file))
    def save_database(self, buffer):
        try:
            return add_obj(CapTrueLogItem(
                secondaryCoilId=buffer.coilId,
                cameraId =capTureConfig.index(self.name),
                cameraName=self.name,
                imageIndex=buffer.save_index
            ))
        except Exception as e:
            logger.error(e)

    def save(self, buffer):
        logger.debug(f"save folder: {self.saveFolder / buffer.coilId}  index: {buffer.save_index}")
        self.save_database(buffer)

        buffer: SickBuffer
        self.save_json(buffer)
        self.save3_d(buffer)
        self.save2_d(buffer)
        try:
            self.save_area_2d(buffer)
        except Exception as e:
            print(e)
        if buffer.save_index == 0:
            if self.camera:
                self.save_camera_config(buffer)

    def run(self):
        while self.running:
            data = self.queue.get()
            self.save(data)
