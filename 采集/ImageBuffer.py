import datetime

import numpy as np
from harvesters.core import Buffer
from CoilDataBase.models.SecondaryCoil import SecondaryCoil


class BufferBase:
    pass

    def __init__(self):
        self.coilData: SecondaryCoil|None = None
        self.coilId = None
        
    def setCoil(self, coil_data: SecondaryCoil):
        self.coilData = coil_data
        self.coilId = str(coil_data.Id)

class SickBuffer(BufferBase):
    def __init__(self, buffer):
        super().__init__()
        self.bdConfig = None
        buffer: Buffer
        self.timestamp = buffer.timestamp
        self.timestamp_frequency = buffer.timestamp_frequency
        self.width = buffer.payload.components[0].width
        self.height = buffer.payload.components[0].height
        self.data3D: np.array = buffer.payload.components[0].data.reshape((self.height, self.width)).copy()
        self.data2D: np.array = buffer.payload.components[1].data.reshape((self.height, self.width)).copy()
        self.save_index = 0


        self.data2D_mean = 0
        self.data3D_mean = 0
        self.timeStr = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S:%f')
        self.area_cap = None



    def get_json(self):
        js_data = {
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
            js_data["coilData"] = self.coilData.get_json()
        if self.bdConfig:
            js_data["bdConfig"] = self.bdConfig
        return js_data

    def setBDconfig(self, bdConfig):
        self.bdConfig = bdConfig


class DaHengBuffer(BufferBase):
    def __init__(self, buffer):
        super().__init__()
        self.buffer  = buffer
        self.data2D = buffer
        self.coilId = None
        self.save_index = 0
        self.timeStr = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S:%f')
        self.save_all = True

    def if_save_index(self):
        if self.save_all:
            return True
        if self.save_index < 10:
            return False
        if self.save_index % 2:
            return False
        return True
