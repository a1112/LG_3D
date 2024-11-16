import time
from threading import Thread

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
        self.globCameraInfo = self.getCameraConfig()

    def getCameraConfig(self):
        # print(self.camera.remote_device.node_map.load_xml_from_file)
        reDict = {}
        for itemName in dir(self.camera.remote_device.node_map):
            try:
                item = getattr(self.camera.remote_device.node_map, itemName)
                reDict[itemName] = item.value
            except BaseException as e:
                pass
        print(reDict)

        return reDict

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

    def getBuffer(self) -> Buffer:
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
