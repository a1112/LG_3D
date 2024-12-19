import datetime
import json
from pathlib import Path
from typing import List, Optional

import numpy as np

import Globs
from CoilDataBase.Coil import addCoilState, addServerDetectionError
from CoilDataBase.models.CoilState import CoilState as CoilStateDB
from CoilDataBase.models.SecondaryCoil import SecondaryCoil
from CoilDataBase.models.AlarmTaperShape import AlarmTaperShape
from CoilDataBase.models.AlarmLooseCoil import AlarmLooseCoil
from CoilDataBase.models.ServerDetectionError import ServerDetectionError
from Globs import control
from property.Types import BdData, LevelingType
from property.detection3D import FlatRollData
from tools import tool, FlattenSurface


def sublist_with_indices(input_list, x, offset=0):
    result = []
    temp = []
    start_index = None

    for i, item in enumerate(input_list):
        item = float(item)
        if item < x:
            if start_index is None:  # 记录子列表的起始位置
                start_index = i + offset
            temp.append(item)
        else:
            if temp:
                result.append([start_index, len(temp), temp])
                temp = []
                start_index = None
    return result


class CoilLineData:
    def __init__(self):
        self.dataIntegration = None
        self.centre = None
        self.lineData = None
        self.rotation_angle = None
        self.linePoint = None
        self.zeroValue = -300
        self.subList = []
        self.max_width = 0
        self.max_width_mm = 0
        self.data = {
        }

    def detection(self):

        px = self.linePoint[0]
        self.subList = sublist_with_indices(self.lineData[self.linePoint[0]:self.linePoint[1]], self.zeroValue, px)
        self.data["subList"] = self.subList
        self.max_width = 0
        for subItem in self.subList:
            if subItem[1] > self.max_width:
                self.max_width = subItem[1]
                self.max_width_mm = self.max_width * self.dataIntegration.scan3dCoordinateScaleY  # x 未标定

        return self.subList

    def get_alarm_loose_coil(self):
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

    def __init__(self, coil_id, save_folder, direction, key):
        self.angleData = None
        self.annulus_mask = None
        self._circleConfig_ = None
        self.index = 0
        self._npyData_ = None
        self._hasDetectionError_ = None
        self.coilId = coil_id
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

        self.lineDataDict = {}
        self._npyData_: np.array = None
        self.__npyData__: np.array = None
        # self._image_ = None
        self.npy_image = None
        self.pil_image = None

        # self._maskImage_ = None
        self.npy_mask = None
        self.pil_mask = None
        self.saveFolder = save_folder

        self.datas = None
        self.configDatas = None

        self.flatRollData: Optional[FlatRollData] = None
        self.detectionLineData = []
        self.alarmTaperShapeList: List[AlarmTaperShape] = []
        self.json_data: dict = {}

        self.currentSecondaryCoil: Optional[SecondaryCoil] = None
        self.__median_non_zero__ = None
        if Globs.control.leveling_3d and Globs.control.leveling_type == LevelingType.WK_TYPE:
            self.__median_non_zero__ = Globs.control.leveling_3d_wk_default_value

    def set_npy_data(self, npy_data):
        print("set set_npy_data", npy_data.shape)
        self.__npyData__ = npy_data

    @property
    def circle_config(self):
        if self._circleConfig_ is None:
            self._circleConfig_ = tool.getCircleConfigByMask(self.npy_mask)
            self.set("width", int(self.width))
            self.set("height", int(self.height))
            self.set("circleConfig", self._circleConfig_)
        return self._circleConfig_

    @property
    def secondaryCoilId(self):
        return self.coilId

    @property
    def surface(self):
        return self.key

    @property
    def width(self):
        return self.__npyData__.shape[1]

    @property
    def height(self):
        return self.__npyData__.shape[0]

    def x_to_mm(self, x_value):
        return x_value * self.scan3dCoordinateScaleX

    def z_to_mm(self, z_value):
        return float((z_value - self.median_non_zero) * self.scan3dCoordinateScaleZ)

    def zero_mm(self):
        return self.z_to_mm(0)

    def point_to_mm(self, arr):
        arr = arr.copy()
        arr[:, 2] = (arr[:, 2] - self.median_non_zero) * self.scan3dCoordinateScaleZ
        return arr

    def get_save_url(self, *args):
        return Path(self.saveFolder, str(self.coilId), *args)

    def isNone(self):
        return self.__npyData__ is None

    @property
    def accuracy_x(self):
        return self.scan3dCoordinateScaleX

    @property
    def accuracy_y(self):
        return self.scan3dCoordinateScaleY

    def annular_region_mean(self, image, r1, r2):
        # 创建坐标网格
        cw = image.shape[0] // 2
        r1 = cw*r1
        r2 = cw*r2
        center_x, center_y,circlexRadius = self.circle_config["inner_circle"]["circlex"]
        y, x = np.indices(image.shape)
        distance = np.sqrt((x - center_x) ** 2 + (y - center_y) ** 2)
        annulus_mask = (distance >= r1) & (distance <= r2)
        annular_mean_area = image[annulus_mask]
        annular_mean_area = annular_mean_area[annular_mean_area != 0]
        annular_mean = np.median(annular_mean_area)
        return annular_mean, annulus_mask

    @property
    def median_non_zero(self):
        if self.__median_non_zero__ is None:
            self.__median_non_zero__, self.annulus_mask = self.annular_region_mean(self.__npyData__,0.6,0.8)  # 获取平均值
        return self.__median_non_zero__

    @property
    def npy_data(self):
        if self._npyData_ is None:
            self._npyData_ = np.where(
                self.__npyData__ < max(self.median_non_zero - 300 // self.scan3dCoordinateScaleZ, 10),
                np.zeros(self.__npyData__.shape), 2 * self.median_non_zero - self.__npyData__)
            self.set("median_3d", self.median_non_zero)
            self.set("median_3d_mm", self.median_3d_mm)
        return self._npyData_

    @property
    def median_3d_mm(self):
        return self.median_non_zero * self.scan3dCoordinateScaleZ

    def get_bd_xyz(self):
        return [self.scan3dCoordinateScaleX, self.scan3dCoordinateScaleX, self.scan3dCoordinateScaleZ]

    def set_start(self):
        self.startTime = datetime.datetime.now()
        self.dictData["startTime"] = self.startTime

    def set_original_data(self, datas):
        self.originalData = datas
        self.bdList = []
        for camera in datas:
            bd_item = BdData(camera['json'][0]["bdConfig"])
            self.bdList.append(bd_item)
            self.coilData = camera['json'][0]["coilData"]
            self.use = self.coilData["Weight"]
            self.scan3dCoordinateScaleX = bd_item.bdDataX.scan3dCoordinateScale
            self.scan3dCoordinateScaleY = bd_item.bdDataY.scan3dCoordinateScale
            self.scan3dCoordinateScaleZ = bd_item.bdDataZ.scan3dCoordinateScale
            self.dictData["scan3dCoordinateScaleX"] = self.scan3dCoordinateScaleX
            self.dictData["scan3dCoordinateScaleY"] = self.scan3dCoordinateScaleY
            self.dictData["scan3dCoordinateScaleZ"] = self.scan3dCoordinateScaleZ

    def set_datas(self, datas):
        self.datas = datas

    def set_cross_points(self, cross_points):
        self.crossPoints = cross_points
        self.dictData["crossPoints"] = cross_points

    def get_datas_info(self, datas):
        def get_shape_list(datas_):
            shapeList = []
            for data in datas_:
                shapeList.append(data['2D'].shape)
            return shapeList

        return {
            "cameraLen": len(datas),  # 摄像头数量
            "shapeList": get_shape_list(datas),
            "startTime": self.startTime,
            "crossPoints": self.crossPoints,  # 裁剪数据
        }

    def set(self, key, value):
        print(f" {self.surface} set -> {key} : {value}")
        self.dictData[key] = value
        self.__dict__[key] = value

    @property
    def upper_limit(self):
        self.dictData["upperLimit"] = control.upper_limit / self.scan3dCoordinateScaleZ
        return self.dictData["upperLimit"]

    @property
    def lower_limit(self):
        self.dictData["lowerLimit"] = control.lower_limit / self.scan3dCoordinateScaleZ
        return self.dictData["lowerLimit"]

    def set_telescoped_alarms(self):
        mask = self.npy_mask
        mask_area = np.count_nonzero(mask)
        npyArea = self.npy_data[mask > 0]
        lower = npyArea[npyArea < (self.__median_non_zero__ + self.lower_limit)]
        upper = npyArea[npyArea > (self.__median_non_zero__ + self.upper_limit)]
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
        print("commit")
        print(self.dictData.get("median_3d"))
        dict_data = self.dictData
        dict_data["startTime"] = dict_data["startTime"].strftime("%Y-%m-%d %H:%M:%S:%f")
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
            jsonData=str(json.dumps(dict_data))
        ))

    def addServerDetectionError(self, errorMsg, errorType="ServerDetectionError"):
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
        self._hasDetectionError_ = True

    def hasDetectionError(self):
        return self._hasDetectionError_

    def __iter__(self):
        return self

    def __next__(self):
        if self.index > 0 or self.isNone():
            self.index = 0
            raise StopIteration
        self.index += 1
        return self

    def flatten_surface_by_rotation(self):
        median_non_zero,annulus_mask=self.annular_region_mean(self.__npyData__,0.6,0.65)  # 获取平均值
        a, b, c, rotated_data, angleData = FlattenSurface.flatten_surface_by_rotation(self.__npyData__,
                                                                                      annulus_mask,
                                                                                      median_non_zero)
        r_z = int(180 - angleData['angle_with_z'])
        print(f"{self.key} 旋转 {r_z} {angleData}")
        self.angleData = angleData
        # return tool.rotate_around_x_axis(self.__npyData__,r_z)
        return r_z


class DataIntegrationList:
    """
    综合数据- List
    """

    def __init__(self):
        self.index = 0
        self.dataIntegrationList: List[DataIntegration] = []

    def append(self, dataIntegration: DataIntegration):
        self.dataIntegrationList.append(dataIntegration)

    def __iter__(self):
        return self

    def __next__(self):
        if self.index < len(self.dataIntegrationList):
            dataIntegration = self.dataIntegrationList[self.index]
            self.index += 1
            if dataIntegration.isNone():
                return self.__next__()
            return dataIntegration
        else:
            self.index = 0
            raise StopIteration
