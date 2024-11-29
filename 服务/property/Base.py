import datetime
import json
from pathlib import Path
from typing import List, Optional

import numpy as np

from CoilDataBase.Coil import addCoilState, addServerDetectionError
from CoilDataBase.models import CoilState as CoilStateDB, AlarmLooseCoil, AlarmFlatRoll, AlarmTaperShape, SecondaryCoil
from CoilDataBase.models import ServerDetectionError
from property.detection3D import FlatRollData


def sublist_with_indices(input_list, x,offset=0):
    result = []
    temp = []
    start_index = None

    for i, item in enumerate(input_list):
        item=float(item)
        if item < x:
            if start_index is None:  # 记录子列表的起始位置
                start_index = i+offset
            temp.append(item)
        else:
            if temp:
                result.append([start_index,len(temp), temp])
                temp = []
                start_index = None
    return result


class BdItem:
    def __init__(self, bdConfig):
        self.bdConfig = bdConfig
        self.scan3dAxisMax = bdConfig["Scan3dAxisMax"]
        self.scan3dAxisMin = bdConfig["Scan3dAxisMin"]
        self.scan3dCoordinateOffset = bdConfig["Scan3dCoordinateOffset"]
        self.scan3dCoordinateScale = bdConfig["Scan3dCoordinateScale"]


class BdData:
    def __init__(self, bdConfig):
        self.bdConfig = bdConfig
        try:
            self.bdDataX = BdItem(bdConfig["CoordinateA"])
            self.bdDataY = BdItem(bdConfig["CoordinateB"])
            self.bdDataZ = BdItem(bdConfig["CoordinateC"])
        except BaseException as e:
            self.bdDataX = BdItem({
                "Scan3dAxisMax": 2559.0,
                "Scan3dAxisMin": 0.0,
                "Scan3dCoordinateOffset": -63.648475646972656,
                "Scan3dCoordinateScale": 0.33943653106689453
            })
            self.bdDataY = BdItem({
                "Scan3dAxisMax": 3.4028234663852886e+38,
                "Scan3dAxisMin": -3.4028234663852886e+38,
                "Scan3dCoordinateOffset": 0.0,
                "Scan3dCoordinateScale": 1.0
            })
            self.bdDataZ = BdItem({
                "Scan3dAxisMax": 65535.0,
                "Scan3dAxisMin": 1.0,
                "Scan3dCoordinateOffset": 3140.954345703125,
                "Scan3dCoordinateScale": 0.016115527600049973
            })


class CoilLineData:
    def __init__(self):
        self.dataIntegration=None
        self.centre=None
        self.lineData=None
        self.rotation_angle=None
        self.linePoint=None
        self.zeroValue=-300
        self.subList=[]
        self.max_width = 0
        self.max_width_mm = 0
        self.data={
        }


    def detection(self):

        px =self.linePoint[0]
        self.subList=sublist_with_indices(self.lineData[self.linePoint[0]:self.linePoint[1]],self.zeroValue,px)
        self.data["subList"]=self.subList
        self.max_width=0
        for subItem in self.subList:
            if subItem[1]>self.max_width:
                self.max_width=subItem[1]
                self.max_width_mm = self.max_width*self.dataIntegration.scan3dCoordinateScaleY # x 未标定

        return self.subList

    def getAlarmLooseCoil(self):
        return AlarmLooseCoil(
            secondaryCoilId=self.dataIntegration.coilId,
            surface=self.dataIntegration.key,
            rotation_angle=self.rotation_angle,
            max_width=self.max_width,
            data=json.dumps(self.data)
        )


class DataIntegration:
    """
    数据整合
    """
    def __init__(self, coilId,saveFolder, direction, key):
        self._hasDetectionError_ = None
        self.coilId = coilId
        self.direction = direction
        self.key = key
        self.startTime = datetime.datetime.now()
        self.datas = None
        self.originalData = None
        self.dictData = {
            "coilId": self.coilId,
            "direction": self.direction,
            "startTime": self.startTime
        }
        self.crossPoints = []
        self.bdList = List[BdData]
        self.coilData = None
        self.use = None
        self.scan3dCoordinateScaleX = None
        self.scan3dCoordinateScaleY = None
        self.scan3dCoordinateScaleZ = None

        import numpy as np
        self.npyData:np.array = None
        # self._image_ = None
        self.npy_image = None
        self.pil_image = None

        # self._maskImage_ = None
        self.npy_mask=None
        self.pil_mask=None
        self.saveFolder=saveFolder

        self.datas=None
        self.configDatas=None

        self.flatRollData: Optional[FlatRollData] =None
        self.detectionLineData= []
        self.alarmTaperShapeList:List[AlarmTaperShape]=[]
        self.json_data : dict={}
        self.circleConfig={}

        self.currentSecondaryCoil: Optional[SecondaryCoil] =None


        self.__median_non_zero__=None

    def get_save_url(self,*args):
        return Path(self.saveFolder, str(self.coilId),*args)

    def isNone(self):
        return self.npyData is None

    @property
    def median_non_zero(self):
        if self.__median_non_zero__ is None:
            def annular_region_mean(image, center_x, center_y, r1, r2):
                # 创建坐标网格
                y, x = np.indices(image.shape)
                distance = np.sqrt((x - center_x) ** 2 + (y - center_y) ** 2)
                annulus_mask = (distance >= r1) & (distance <= r2)
                annular_mean_area = image[annulus_mask]
                annular_mean_area = annular_mean_area[annular_mean_area != 0]
                annular_mean = np.median(annular_mean_area)
                return annular_mean
            cw = self.npyData.shape[0] // 2
            self.__median_non_zero__ = annular_region_mean(self.npyData, self.circleConfig["inner_circle"]["circlex"][0],
                                                  self.circleConfig["inner_circle"]["circlex"][1],
                                                  int(cw * 0.6),
                                                  int(cw * 0.8))  # 获取平均值
            # 将输入的矩阵转换为 numpy 数组  翻转
            # 创建一个新的矩阵，应用条件变换
            # transformed_matrix = np.where(matrix < n, matrix, 2 * a - matrix)
            self.npyData = np.where(self.npyData < max(self.__median_non_zero__-300//self.scan3dCoordinateScaleZ,10), np.zeros(self.npyData.shape), 2 * self.__median_non_zero__ - self.npyData)

        return self.__median_non_zero__

    @property
    def median_3d_mm(self):
        return self.__median_non_zero__*self.scan3dCoordinateScaleZ


    def getBdXYZ(self):
        return  [self.scan3dCoordinateScaleX,self.scan3dCoordinateScaleX,self.scan3dCoordinateScaleZ]

    def setStart(self):
        self.startTime = datetime.datetime.now()
        self.dictData["startTime"] = self.startTime

    def setOriginalData(self, datas):
        self.originalData = datas
        self.bdList = []
        for camera in datas:
            bdItem = BdData(camera['json'][0]["bdConfig"])
            self.bdList.append(bdItem)
            self.coilData = camera['json'][0]["coilData"]
            self.use = self.coilData["Weight"]
            self.scan3dCoordinateScaleX = bdItem.bdDataX.scan3dCoordinateScale
            self.scan3dCoordinateScaleY = bdItem.bdDataY.scan3dCoordinateScale
            self.scan3dCoordinateScaleZ = bdItem.bdDataZ.scan3dCoordinateScale
            self.dictData["scan3dCoordinateScaleX"] = self.scan3dCoordinateScaleX
            self.dictData["scan3dCoordinateScaleY"] = self.scan3dCoordinateScaleY
            self.dictData["scan3dCoordinateScaleZ"] = self.scan3dCoordinateScaleZ

    def setDatas(self, datas):
        self.datas = datas

    def setCrossPoints(self, crossPoints):
        self.crossPoints = crossPoints
        self.dictData["crossPoints"] = crossPoints

    def getDatasInfo(self, datas):
        def getShapeList(datas_):
            shapeList = []
            for data in datas_:
                shapeList.append(data['2D'].shape)
            return shapeList

        return {
            "cameraLen": len(datas),  # 摄像头数量
            "shapeList": getShapeList(datas),
            "startTime": self.startTime,
            "crossPoints": self.crossPoints,  # 裁剪数据
        }

    def set(self, key, value):
        self.dictData[key] = value
        self.__dict__[key] = value

    @property
    def upperLimit(self):
        self.dictData["upperLimit"] = 75 / self.scan3dCoordinateScaleZ
        return self.dictData["upperLimit"]

    @property
    def lowerLimit(self):
        self.dictData["lowerLimit"] = -75 / self.scan3dCoordinateScaleZ
        return self.dictData["lowerLimit"]

    def setTelescopedAlarms(self):
        mask = self.npy_mask
        mask_area = np.count_nonzero(mask)
        npyArea = self.npyData[mask > 0]
        lower = npyArea[npyArea < (self.__median_non_zero__ + self.lowerLimit)]
        upper = npyArea[npyArea > (self.__median_non_zero__ + self.upperLimit)]
        lowerArea = np.count_nonzero(lower)
        upperArea = np.count_nonzero(upper)
        self.set("lowerArea", lowerArea)
        self.set("upperArea", upperArea)
        lowerArea_percent = lowerArea / mask_area
        upperArea_percent = upperArea / mask_area
        self.set("lowerArea_percent", lowerArea_percent)
        self.set("upperArea_percent", upperArea_percent)
        self.set("mask_area", mask_area)

    def commit(self):
        # 数据提交
        dictData=self.dictData
        dictData["startTime"]=dictData["startTime"].strftime("%Y-%m-%d %H:%M:%S:%f")
        addCoilState(CoilStateDB(
            secondaryCoilId=self.coilId,
            surface=self.key,
            startTime=self.startTime,
            scan3dCoordinateScaleX=self.scan3dCoordinateScaleX,
            scan3dCoordinateScaleY=self.scan3dCoordinateScaleY,
            scan3dCoordinateScaleZ=self.scan3dCoordinateScaleZ,
            rotate=self.dictData.get("rotate"),
            x_rotate=self.dictData.get("x_rotate"),
            median_3d=self.dictData.get("median_3d"),
            median_3d_mm=self.dictData.get("median_3d_mm"),
            colorFromValue_mm=self.dictData.get("colorFromValue_mm"),
            colorToValue_mm=self.dictData.get("colorToValue_mm"),
            start=self.dictData.get("start"),
            step=self.dictData.get("step"),
            upperLimit=self.dictData.get("upperLimit"),
            lowerLimit=self.dictData.get("lowerLimit"),
            lowerArea=self.dictData.get("lowerArea"),
            upperArea=self.dictData.get("upperArea"),
            lowerArea_percent=self.dictData.get("lowerArea_percent"),
            upperArea_percent=self.dictData.get("upperArea_percent"),
            mask_area=self.dictData.get("mask_area"),
            width=self.dictData.get("width"),
            height=self.dictData.get("height"),
            jsonData=str(json.dumps(dictData)),
        ))

    def addServerDetectionError(self,errorMsg,errorType="ServerDetectionError"):
        """
        添加服务器检测错误
        """
        addServerDetectionError(
            ServerDetectionError(
                secondaryCoilId=self.coilId,
                surface=self.key,
                errorType=errorType,
                msg=errorMsg
            )
        )
        self._hasDetectionError_=True

    def hasDetectionError(self):
        return self._hasDetectionError_

class DataIntegrationList:
    """
    综合数据- List
    """
    def __init__(self):
        self.index = 0
        self.dataIntegrationList:List[DataIntegration] = []

    def append(self,dataIntegration:DataIntegration):
        self.dataIntegrationList.append(dataIntegration)

    def __iter__(self):
        return self

    def __next__(self):
        if self.index < len(self.dataIntegrationList):
            dataIntegration = self.dataIntegrationList[self.index]
            if dataIntegration.isNone():
                return self.__next__()
            self.index += 1
            return dataIntegration
        else:
            raise StopIteration