import time
from threading import Thread
from typing import Any
import CONFIG
from CoilDataBase.models.SecondaryCoil import SecondaryCoil
from ImageDataSave import ImageDataSave
from ImageBuffer import SickBuffer, DaHengBuffer
from Signal import signal, lastTimeDict
from pathlib import Path
from Camera import SickCamera, DaHengCamera
from Log import logger
import Server
from CameraControl import CameraControl


class CapTureBase(Thread):
    def __init__(self, dataSave:ImageDataSave,camera, parent, cameraInfo):
        self.parent = parent
        self.camera = camera
        self.dataSave = dataSave
        self.cameraInfo = cameraInfo
        self.running = True
        super().__init__()
        pass

class CapTure2D(CapTureBase):
    def __init__(self, dataSave:ImageDataSave, camera, parent, cameraInfo):
        super().__init__(dataSave, camera, parent, cameraInfo)
        pass

    def run(self):
        while self.running:
            try:
                # if not self.c:
                #     time.sleep(0.1)
                #     continue

                coil = self.parent.coil
                if coil is None:
                    print(f"coil 为空: ",self.parent.coil)
                    time.sleep(0.1)
                    coil = 1
                try:
                    area_cap, last_time = self.camera.get_last_frame(timeout=2)
                except TimeoutError:
                    camera_status = self.camera.get_status() if hasattr(self.camera, "get_status") else {}
                    if camera_status.get("connected", False):
                        self.parent.last_error_2d = ""
                    else:
                        self.parent.last_error_2d = camera_status.get("lastError", "2D camera disconnected")
                    time.sleep(0.05)
                    continue
                bf = DaHengBuffer(area_cap,last_time)
                # bf.setBDconfig(cap.getBDconfig())
                bf.setCoil(coil)
                self.dataSave.put(bf)
                lastTimeDict[self.cameraInfo.key] = time.time()
                self.parent.last_frame_time_2d = time.time()
                self.parent.last_error_2d = ""
                self.parent.missed_in_without_frame = 0
                self.parent.reconnect_attempts = 0

            except BaseException as e:
                self.parent.last_error_2d = str(e)
                logger.debug(f"相机 {self.cameraInfo.key} 异常 {e}")
                time.sleep(5)

class CapTure3D(CapTureBase):
    def __init__(self, dataSave:ImageDataSave, camera, parent, cameraInfo):
        super().__init__(dataSave, camera, parent, cameraInfo)
        pass

    def run(self):
        while self.running:
            try:
                # if not self.c:
                #     time.sleep(0.1)
                #     continue
                logger.debug(f"启动相机 ...  ")

                with self.camera as cap:
                    logger.debug(f"启动相机 {self.camera}... ...")
                    while True:
                        try:
                            coil = self.parent.coil
                            if coil is None:
                                print(f"coil 为空: ",self.parent.coil)
                                time.sleep(0.1)
                                coil = 1
                            buffer = cap.get_buffer()
                            bf = SickBuffer(buffer)
                            bf.setBDconfig(cap.getBDconfig())
                            bf.setCoil(coil)
                            # bf.area_cap = self.camera.get_last_frame()
                            self.dataSave.put(bf)
                            lastTimeDict[self.cameraInfo.key] = time.time()
                            self.parent.last_frame_time_3d = time.time()
                            self.parent.last_error_3d = ""
                        finally:
                            buffer.queue()
            except BaseException as e:
                self.parent.last_error_3d = str(e)
                logger.debug(f"相机 {self.cameraInfo.key} 异常 {e}")
                time.sleep(5)

class CapTure(Thread):
    """
        多线程的主循环
    """
    def __init__(self, camera_info:CONFIG.CameraConfig, start_camera_server=True):
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
        self.camera_3d = None
        self.camera_2d = None
        self.camera_info = camera_info
        self.start_camera_server = start_camera_server
        self.last_frame_time_2d = 0
        self.last_frame_time_3d = 0
        self.started_at = time.time()
        self.last_trigger_in_time = 0
        self.last_error_2d = ""
        self.last_error_3d = ""
        self.missed_in_without_frame = 0
        self.reconnect_attempts = 0


    def set_camera_3d(self):
        if self.cameraInfo.cap3D:
            camera = SickCamera(self.cameraInfo.sn)
            self.camera = camera
            return camera
        return None

    def set_camera_2d(self):
        if self.cameraInfo.cap2D:
            # if self.cameraInfo.key not in ["Cap_L_D","Cap_L_U","Cap_L_M"]:
            #     return None
            yaml_config = self.cameraInfo.yaml_config
            camera = DaHengCamera(yaml_config, camera_key=self.cameraInfo.key)
            return camera
        return None

    def get_value(self, key, default):
        if key in self.camera_info:
            return self.camera_info[key]
        return default

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
            now = time.time()
            if self.last_frame_time_2d <= self.last_trigger_in_time:
                self.missed_in_without_frame += 1
                logger.warning(f"2D camera {self.cameraInfo.key} no frame between triggerIn, count={self.missed_in_without_frame}")
                last_frame_age = now - self.last_frame_time_2d if self.last_frame_time_2d else None
                if (
                    self.missed_in_without_frame >= 10
                    and self.camera_2d
                    and getattr(self.camera_2d, "connected", False)
                    and (last_frame_age is None or last_frame_age > 120)
                ):
                    self.reconnect_attempts += 1
                    logger.warning(
                        f"2D camera {self.cameraInfo.key} forcing reconnect after repeated missing frames "
                        f"(count={self.missed_in_without_frame}, last_frame_age={last_frame_age}, "
                        f"attempt={self.reconnect_attempts})"
                    )
                    self.camera_2d.request_reconnect()
                    self.missed_in_without_frame = 0
                    if self.reconnect_attempts > 5:
                        logger.error(
                            f"2D camera {self.cameraInfo.key} exceeded 5 reconnect attempts, "
                            "keep retrying this camera only"
                        )
            else:
                self.missed_in_without_frame = 0
            self.last_trigger_in_time = now
        elif sig_type == "out":
            self.dataSave.trigger_out(coil)
            self.captureRunning = False

    def run(self):
        camera_info = CONFIG.CameraConfig(self.camera_info)
        self.cameraInfo = camera_info
        self.saveFolder = Path(camera_info.saveFolder) / camera_info.key
        self.running = True
        self.captureRunning = False
        self.globCapInfo = {}
        self.camera = None
        self.dataSave = ImageDataSave(self.saveFolder)
        self.cameraControl = CameraControl(self)
        self.coil:SecondaryCoil|None = None
        signal.register(self.on_signal)


        if self.start_camera_server:
            Server.start_server(camera_info, self)
        logger.debug(f"启动采集 线程 {self.cameraInfo.key}... ...")


        camera_3d = self.set_camera_3d()
        camera_2d = self.set_camera_2d()
        self.camera_3d = camera_3d
        self.camera_2d = camera_2d

        if camera_2d is not None:
            logger.debug("启动 2D CapTrue")
            CapTure2D(self.dataSave,camera_2d, self, self.cameraInfo).start()

        if camera_3d is not None:
            logger.debug("启动 3D CapTrue")
            CapTure3D(self.dataSave,camera_3d, self, self.cameraInfo).start()


        # while self.running:
        #     try:
        #         # if not self.c:
        #         #     time.sleep(0.1)
        #         #     continue
        #         logger.debug(f"启动相机 ...  ")
        #
        #         with camera_3d as cap:
        #             logger.debug(f"启动相机 {camera_3d}... ...")
        #             while True:
        #                 try:
        #                     if self.coil is None:
        #                         print(f"coil 为空 ")
        #                         time.sleep(0.1)
        #                         self.coil = 1
        #                     buffer = cap.get_buffer()
        #                     bf = SickBuffer(buffer)
        #                     bf.setBDconfig(cap.getBDconfig())
        #                     bf.setCoil(self.coil)
        #                     bf.area_cap = camera_2d.get_last_frame()
        #                     self.dataSave.put(bf)
        #                     lastTimeDict[self.cameraInfo.key] = time.time()
        #                 finally:
        #                     buffer.queue()
        #     except BaseException as e:
        #         logger.debug(f"相机 {self.cameraInfo.key} 异常 {e}")
        #         time.sleep(5)

    def release(self):
        pass

    def getCreatedFile(self, clear=False):
        if self.dataSave is None:
            return []
        return self.dataSave.get_created_files(clear=clear)

    def get_capture_status(self) -> dict[str, Any]:
        camera_info = self.cameraInfo or CONFIG.CameraConfig(self.camera_info)
        now = time.time()
        status = {
            "key": camera_info.key,
            "name": camera_info.name,
            "sn": camera_info.sn,
            "cap2D": bool(camera_info.cap2D),
            "cap3D": bool(camera_info.cap3D),
            "captureRunning": bool(self.captureRunning),
            "startedAt": self.started_at,
            "lastFrameTime2D": self.last_frame_time_2d,
            "lastFrameAge2D": now - self.last_frame_time_2d if self.last_frame_time_2d else None,
            "lastFrameTime3D": self.last_frame_time_3d,
            "lastFrameAge3D": now - self.last_frame_time_3d if self.last_frame_time_3d else None,
            "lastError2D": self.last_error_2d,
            "lastError3D": self.last_error_3d,
            "missedInWithoutFrame": self.missed_in_without_frame,
            "reconnectAttempts": self.reconnect_attempts,
            "coilId": getattr(self.coil, "Id", None),
            "coilNo": getattr(self.coil, "CoilNo", ""),
            "serviceReady": self.cameraControl is not None,
            "camera2D": None,
        }
        if self.cameraControl is not None:
            try:
                status["camera2D"] = self.cameraControl.get_2d_status()
            except Exception as e:
                status["camera2D"] = {
                    "ok": False,
                    "connected": False,
                    "message": str(e),
                }
        return status
