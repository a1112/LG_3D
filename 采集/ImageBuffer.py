import datetime

import numpy as np
from harvesters.core import Buffer
import DataSave


class SickBuffer:
    def __init__(self, buffer):
        self.bdConfig = None
        buffer: Buffer
        self.timestamp = buffer.timestamp
        self.timestamp_frequency = buffer.timestamp_frequency
        self.width = buffer.payload.components[0].width
        self.height = buffer.payload.components[0].height
        self.data3D: np.array = buffer.payload.components[0].data.reshape((self.height, self.width)).copy()
        self.data2D: np.array = buffer.payload.components[1].data.reshape((self.height, self.width)).copy()
        self.save_index = 0
        self.coilId = None
        self.coilData: DataSave.SecondaryCoil = None
        self.data2D_mean = 0
        self.data3D_mean = 0
        self.timeStr = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S:%f')

    def setCoil(self, coilData: DataSave.SecondaryCoil):
        self.coilData = coilData
        self.coilId = str(coilData.Id)

    def get_json(self):
        jsData = {
            "timestamp": self.timestamp,
            "timestamp_frequency": self.timestamp_frequency,
            "width": self.width,
            "height": self.height,
            "save_index": self.save_index,
            "coilId": self.coilId,
            "data2D_mean": self.data2D_mean,
            "data3D_mean": self.data3D_mean,
            "capTime": self.timeStr
        }
        if self.coilData:
            jsData["coilData"] = self.coilData.get_json()
        if self.bdConfig:
            jsData["bdConfig"] = self.bdConfig
        return jsData

    def setBDconfig(self, bdConfig):
        self.bdConfig = bdConfig
