import threading
from multiprocessing import Process, Queue
import time
from threading import Thread
import queue

import CONFIG
from BKVisionCamera import crate_capter
from harvesters.core import ImageAcquirer,Buffer

from Log import logger
from core import get_camera_by_sn


class SickCamera:
    def __init__(self, sn):
        super().__init__()
        self.sn = sn
        self.camera = get_camera_by_sn(sn)
        if self.camera is None:
            raise Exception(f"相机 初始化失败: {sn}")
        self.setConfig()
        self.camera:ImageAcquirer
        self.globCameraInfo = self.get_camera_config()


    def get_camera_config(self):
        # print(self.camera.remote_device.node_map.load_xml_from_file)
        re_dict = {}
        for itemName in dir(self.camera.remote_device.node_map):
            try:
                item = getattr(self.camera.remote_device.node_map, itemName)
                re_dict[itemName] = item.value
            except BaseException as e:
                pass
        print(re_dict)

        return re_dict

    def setConfig(self):
        # self.camera.remote_device.node_map
        # self.camera.remote_device.node_map.TriggerMode.value = "On"
        self.camera.remote_device.node_map.DeviceScanType.value = "Linescan3D"

    def getBDconfig(self):
        bdData = {}
        for key in ["CoordinateA", "CoordinateB", "CoordinateC"]:
            self.camera.remote_device.node_map.Scan3dCoordinateSelector.value = key
            bdData[key] = {
                "Scan3dCoordinateOffset": self.camera.remote_device.node_map.Scan3dCoordinateOffset.value,
                "Scan3dCoordinateScale": self.camera.remote_device.node_map.Scan3dCoordinateScale.value,
                "Scan3dAxisMax": self.camera.remote_device.node_map.Scan3dAxisMax.value,
                "Scan3dAxisMin": self.camera.remote_device.node_map.Scan3dAxisMin.value,
                # "Scan3dInvalidDataValue": self.camera.remote_device.node_map.Scan3dInvalidDataValue.value,
                # "Scan3dRectificationSpread": self.camera.remote_device.node_map.Scan3dRectificationSpread.value,
            }
        return bdData

    def get_buffer(self) -> Buffer:
        return self.camera.fetch()

    def open(self):
        sT = time.time()
        self.camera.start()
        eT = time.time()
        print(f"start: {eT-sT} mm")

    def release(self):
        self.camera.stop()

    def __enter__(self):
        # 初始化或打开相机等操作
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # 清理资源，例如关闭相机
        self.release()

    def get_last_frame(self):
        return None

    def if_save_index(self):
        return False

class DaHengCamera(Thread): # Process
    def __init__(self, yaml_config):
        super().__init__()
        self.yaml_config = yaml_config
        self.last_frame = None
        self.last_frame_time = 0
        self.frame_queue = Queue()
        self._reconnect_event = threading.Event()
        self.daemon = True
        if yaml_config:
            self.start()

    def _create_capter(self):
        return crate_capter(str(CONFIG.CONFIG_DIR / self.yaml_config))

    def _clear_queue(self):
        try:
            while True:
                self.frame_queue.get_nowait()
        except queue.Empty:
            pass

    def _trim_queue(self, max_size):
        try:
            while self.frame_queue.qsize() > max_size:
                self.frame_queue.get_nowait()
        except NotImplementedError:
            try:
                self.frame_queue.get_nowait()
            except queue.Empty:
                pass
        except queue.Empty:
            pass

    def get_last_frame(self, timeout=None):
        if timeout is None:
            return self.frame_queue.get()
        try:
            return self.frame_queue.get(timeout=timeout)
        except queue.Empty:
            raise TimeoutError("2D camera frame timeout")

    def request_reconnect(self):
        self._reconnect_event.set()

    def run(self):
        if not self.yaml_config:
            logger.error("2D camera yaml_config missing, capture thread not started")
            return

        reconnect_delay = 1

        while True:
            try:
                self._reconnect_event.clear()
                self.capter = self._create_capter()
                with self.capter as cap:
                    logger.debug("2D camera connected")
                    self._clear_queue()
                    reconnect_delay = 1
                    self.last_frame_time = time.time()
                    frame_id = 0
                    last_wait_log = 0
                    while True:
                        if self._reconnect_event.is_set():
                            raise RuntimeError("Manual reconnect requested")
                        frame = cap.getFrame()
                        now = time.time()
                        if frame is None:
                            if now - last_wait_log >= 200:
                                wait_s = now - self.last_frame_time
                                logger.debug(f"2D camera waiting for trigger frame (last frame {wait_s:.1f}s ago)")
                                last_wait_log = now
                            time.sleep(0.05)
                            continue
                        self.last_frame_time = now
                        frame_id += 1
                        logger.debug(f"2D frame captured id={frame_id}")
                        self._trim_queue(5)
                        self.frame_queue.put([frame, now])
            except BaseException as e:
                logger.warning(f"2D camera disconnected, retrying in {reconnect_delay}s: {e}")
                self._clear_queue()
                time.sleep(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 2, 5)
