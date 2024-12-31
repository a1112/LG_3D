import time
from threading import Thread
from multiprocessing import Process

import CONFIG
from CoilDataBase.models.SecondaryCoil import SecondaryCoil
from ImageDataSave import ImageDataSave
from ImageBuffer import SickBuffer
from Signal import signal, lastTimeDict
from pathlib import Path
from Camera import SickCamera, DaHengCamera
from Log import logger
import Server
from CameraControl import CameraControl
class CapTure(Thread):
    """
        多线程的主循环
    """
    def __init__(self, camera_info:CONFIG.CameraConfig):
        super().__init__()
        self.cameraControl = None
        self.dataSave = None
        self.camera = None
        self.globCapInfo = None
        self.running = None
        self.saveFolder = None
        self.cameraInfo = None
        self.captureRunning = None
        self.coil = None
        self.camera_info=camera_info


    def set_camera_3d(self):
        camera = SickCamera(self.cameraInfo.sn)
        self.camera = camera
        return camera

    def set_camera_2d(self):
        yaml_config = self.cameraInfo.yaml_config
        camera=DaHengCamera(yaml_config)
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
        camera_info=CONFIG.CameraConfig(self.camera_info)
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
        logger.debug(f"启动采集 线程 {self.cameraInfo.key}... ...")
        camera_3d = self.set_camera_3d()
        camera_2d = self.set_camera_2d()
        while self.running:
            try:
                # if not self.c:
                #     time.sleep(0.1)
                #     continue
                logger.debug(f"启动相机 ...  ")

                with camera_3d as cap:
                    logger.debug(f"启动相机 {camera_3d}... ...")
                    while True:
                        try:
                            if self.coil is None:
                                print(f"coil 为空 ")
                                time.sleep(0.1)
                                self.coil = 1
                            buffer = cap.get_buffer()
                            bf = SickBuffer(buffer)
                            bf.setBDconfig(cap.getBDconfig())
                            bf.setCoil(self.coil)
                            bf.area_cap = camera_2d.get_last_frame()
                            self.dataSave.put(bf)
                            lastTimeDict[self.cameraInfo.key] = time.time()
                        finally:
                            buffer.queue()
            except BaseException as e:
                logger.debug(f"相机 {self.cameraInfo.key} 异常 {e}")
                time.sleep(5)

    def release(self):
        pass
