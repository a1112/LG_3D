import time
from threading import Thread

from ImageDataSave import ImageDataSave
from ImageBuffer import SickBuffer
from Signal import signal, lastTimeDict
from pathlib import Path
from Camera import SickCamera
import DataSave
from Log import logger
import Server
from CameraControl import CameraControl
class CapTure(Thread):
    #  原始数据保存
    def __init__(self, cameraInfo):
        super().__init__()
        self.cameraInfo = cameraInfo
        signal.register(self.onSignal)
        self.saveFolder = Path(cameraInfo["saveFolder"]) / cameraInfo["key"]
        self.running = True
        self.captureRunning = False
        self.globCapInfo = {}
        self.camera = None
        self.dataSave = ImageDataSave(self.saveFolder)
        self.cameraControl = CameraControl(self)
        self.coil:DataSave.SecondaryCoil = None
        Server.startServer(cameraInfo,self)


    def setCamera(self):
        camera = SickCamera(self.cameraInfo["sn"])
        self.camera = camera
        self.dataSave.setCamera(camera)
        return camera

    def get(self):
        pass

    def onSignal(self, sigType, coil):
        # 接收到新的信号
        coilData: DataSave.SecondaryCoil
        self.coil = coil
        if sigType == "init":
            self.dataSave.triggerInit(coil)
            self.captureRunning = True
        elif sigType == "in":
            self.dataSave.triggerIn(coil)
            self.captureRunning = True
        elif sigType == "out":
            self.dataSave.triggerOut(coil)
            self.captureRunning = False

    def run(self):
        logger.debug(f"启动采集 线程 {self.cameraInfo['key']}... ...")
        while self.running:
            try:
                if not self.captureRunning:
                    time.sleep(0.001)
                    continue
                camera = self.setCamera()
                logger.debug(f"启动相机 ...  ")
                with camera as cap:
                    logger.debug(f"启动相机 {camera}... ...")
                    while self.captureRunning:
                        try:
                            buffer = cap.getBuffer()
                            bf = SickBuffer(buffer)
                            bf.setBDconfig(cap.getBDconfig())
                            bf.setCoil(self.coil)
                            self.dataSave.put(bf)
                            lastTimeDict[self.cameraInfo["key"]] = time.time()
                        finally:
                            buffer.queue()
            except BaseException as e:
                logger.debug(f"相机 {self.cameraInfo['key']} 异常 {e}")
                time.sleep(5)
                # raise e

    def release(self):
        pass
