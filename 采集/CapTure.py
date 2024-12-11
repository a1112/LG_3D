import time
from threading import Thread

import CONFIG
from CoilDataBase.models import SecondaryCoil
from ImageDataSave import ImageDataSave
from ImageBuffer import SickBuffer
from Signal import signal, lastTimeDict
from pathlib import Path
from Camera import SickCamera
from Log import logger
import Server
from CameraControl import CameraControl
class CapTure(Thread):
    """
        多线程的主循环
    """
    def __init__(self, camera_info:CONFIG.CameraConfig):
        super().__init__()
        self.cameraInfo = camera_info
        signal.register(self.on_signal)
        self.saveFolder = Path(camera_info.saveFolder) / camera_info.key
        self.running = True
        self.captureRunning = False
        self.globCapInfo = {}
        self.camera = None
        self.dataSave = ImageDataSave(self.saveFolder)
        self.cameraControl = CameraControl(self)
        self.coil:SecondaryCoil|None = None
        Server.start_server(camera_info, self)


    def set_camera(self):
        camera = SickCamera(self.cameraInfo.sn)
        self.camera = camera
        self.dataSave.set_camera(camera)
        return camera

    def get(self):
        pass

    def on_signal(self, sig_type, coil):
        # 接收到新的信号
        coilData: SecondaryCoil
        self.coil = coil
        if sig_type == "init":
            self.dataSave.trigger_init(coil)
            self.captureRunning = True
        elif sig_type == "in":
            self.dataSave.trigger_in(coil)
            self.captureRunning = True
        elif sig_type == "out":
            self.dataSave.trigger_out(coil)
            self.captureRunning = False

    def run(self):
        logger.debug(f"启动采集 线程 {self.cameraInfo.key}... ...")
        while self.running:
            try:
                if not self.captureRunning:
                    time.sleep(0.001)
                    continue
                camera = self.set_camera()
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
                            lastTimeDict[self.cameraInfo.key] = time.time()
                        finally:
                            buffer.queue()
            except BaseException as e:
                logger.debug(f"相机 {self.cameraInfo.key} 异常 {e}")
                time.sleep(5)
                raise e

    def release(self):
        pass
