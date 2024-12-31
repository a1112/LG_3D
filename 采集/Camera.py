import threading
from multiprocessing import Process, Queue
import time
import CONFIG
from BKVisionCamera import crate_capter
from harvesters.core import ImageAcquirer,Buffer

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
        for key in ["CoordinateA","CoordinateB","CoordinateC"]:
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

class DaHengCamera(Process):
    def __init__(self, yaml_config):
        super().__init__()
        self.yaml_config = yaml_config
        self.last_frame = None
        self.frame_queue = Queue()
        if yaml_config:
            self.start()


    def get_last_frame(self):
        if self.frame_queue.qsize() > 0:
            return self.frame_queue.get()
    def run(self):
        print(self.yaml_config)
        self.capter = crate_capter(str(CONFIG.CONFIG_DIR / self.yaml_config))
        while True:
            try:
                with self.capter as cap:
                    while True:
                        frame = cap.getFrame()
                        while self.frame_queue.qsize() > 0:
                            self.frame_queue.get()
                        self.frame_queue.put(frame)
                        if frame is None:
                            time.sleep(0.1)
                            continue
                        time.sleep(0.01)
            except BaseException as e:
                time.sleep(5)
                print(e)