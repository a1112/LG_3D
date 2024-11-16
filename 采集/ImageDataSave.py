import json
from pathlib import Path
from threading import Thread
from queue import Queue

import numpy as np
from PIL import Image
from ImageBuffer import SickBuffer
import DataSave
from Camera import SickCamera
from Log import logger


class ImageDataSave(Thread):
    def __init__(self, saveFolder):
        super().__init__()
        self.saveFolder = Path(saveFolder)
        self.save_index = 0
        self.queue = Queue()
        self.running = True
        self.camera:SickCamera = None
        self.start()

    def setCamera(self, camera):
        self.camera = camera

    def triggerInit(self,coil:DataSave.SecondaryCoil):
        logger.debug(f"triggerInit {coil}")
        image2DFolder = self.saveFolder / str(coil.Id)/ "2d"
        if image2DFolder.exists():
            files = image2DFolder.glob("*")
            self.save_index = len(list(files))

    def triggerIn(self,coil):
        logger.debug(f"triggerIn {coil}")
        self.save_index = 0

    def triggerOut(self,coil):
        pass

    def put(self, buffer: SickBuffer):
        # if buffer.data2D.mean() < 5:
        #     print(buffer.data2D.mean())
        #     return
        buffer.data2D_mean = buffer.data2D.mean()
        buffer.save_index = self.save_index
        self.queue.put(buffer)
        self.save_index += 1

    def saveCameraConfig(self,buffer):
        saveFile = self.saveFolder / buffer.coilId / "camera_config.json"
        saveFile.parent.mkdir(parents=True, exist_ok=True)
        with saveFile.open("w", encoding="utf-8") as f:
            json.dump(self.camera.globCameraInfo, f,indent=4,ensure_ascii=False,sort_keys=True)

    def saveJson(self, buffer):
        buffer: SickBuffer
        saveFile = self.saveFolder / buffer.coilId / "json" / f"{buffer.save_index}.json"
        saveFile.parent.mkdir(parents=True, exist_ok=True)
        with saveFile.open("w", encoding="utf-8") as f:
            json.dump(buffer.get_json(), f,indent=4,ensure_ascii=False,sort_keys=True)

    def save3D(self, buffer):
        buffer: SickBuffer
        saveFile = self.saveFolder / buffer.coilId / "3d" / f"{buffer.save_index}.npy"
        saveFile.parent.mkdir(parents=True, exist_ok=True)
        np.save(str(saveFile), buffer.data3D)
        # saveFile = self.saveFolder / buffer.coilId / "3d_preview" / f"{buffer.save_index}.png"
        # saveFile.parent.mkdir(parents=True, exist_ok=True)
        # data = (buffer.data3D / 256).astype(np.uint8)
        # Image.fromarray(data).save(str(saveFile))

    def save2D(self, buffer):
        saveFile = self.saveFolder / buffer.coilId / "2d" / f"{buffer.save_index}.bmp"
        saveFile.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(buffer.data2D).save(str(saveFile))

    def save(self, buffer):
        logger.debug(f"save folder: {self.saveFolder / buffer.coilId}  index: {buffer.save_index}")
        buffer: SickBuffer
        self.saveJson(buffer)
        self.save3D(buffer)
        self.save2D(buffer)
        if buffer.save_index == 0:
            if self.camera:
                self.saveCameraConfig(buffer)

    def run(self):
        while self.running:
            data = self.queue.get()
            self.save(data)
