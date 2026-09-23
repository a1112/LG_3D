import datetime
import json
import logging
from pathlib import Path
from typing import List, Optional

import numpy as np

import Globs
from CoilDataBase.Coil import addCoilState, add_server_detection_error
from CoilDataBase.models import CoilState as CoilStateDB
from CoilDataBase.models import SecondaryCoil
from CoilDataBase.models import AlarmTaperShape
from CoilDataBase.models import AlarmLooseCoil
from CoilDataBase.models import ServerDetectionError

from AlarmDetection.Result.AlarmData import AlarmData
from Base.CONFIG import infoConfigProperty
from Globs import control
from Base.property.Types import BdData
from Base.tools import tool, FlattenSurface
from Base.utils.Log import logger


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
        self.data = {}

    def _max_width_scale(self):
        for attr in ("scan3dCoordinateScaleX", "scan3dCoordinateScaleY"):
            try:
                scale = float(getattr(self.dataIntegration, attr, 0))
            except (TypeError, ValueError, OverflowError):
                continue
            if np.isfinite(scale) and scale > 0:
                return scale, attr[-1].lower()
        return 1.0, "px"

    def detection(self):

        px = self.linePoint[0]
        self.subList = sublist_with_indices(
            self.lineData[self.linePoint[0]:self.linePoint[1]], self.zeroValue,
            px)
        self.data["subList"] = self.subList
        self.max_width = 0
        width_scale, width_axis = self._max_width_scale()
        self.data["max_width_scale"] = width_scale
        self.data["max_width_scale_axis"] = width_axis
        for subItem in self.subList:
            if subItem[1] > self.max_width:
                self.max_width = subItem[1]
                self.max_width_mm = self.max_width * width_scale

        return self.subList

    def get_alarm_loose_coil(self):
        return AlarmLooseCoil(secondaryCoilId=self.dataIntegration.coilId,
                              surface=self.dataIntegration.key,
                              rotation_angle=self.rotation_angle,
                              max_width=self.max_width_mm,
                              data=json.dumps(
                                  {
                                      **self.data,
                                      "max_width_px": self.max_width,
                                      "max_width_mm": self.max_width_mm,
                                      "max_width_unit": "mm",
                                  },
                                  ensure_ascii=False))


class DataIntegration:
    """
    数据整合
    """

    def __init__(self, coil_id, save_folder, direction, key):
        self.defect_dict = None  # 缺陷字典
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
        self.scan3dCoordinateOffsetX = 0
        self.scan3dCoordinateOffsetY = 0
        self.scan3dCoordinateOffsetZ = 0

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

        self.alarmData = AlarmData(self)
        self.detectionLineData = []
        self.alarmTaperShapeList: List[AlarmTaperShape] = []
        self.json_data: dict = {}

        self.currentSecondaryCoil: Optional[SecondaryCoil] = None
        self.__median_non_zero__ = None

    @property
    def id_str(self):
        return f"{self.coilId}_{self.direction}_{self.key}"

    @property
    def next_code(self):
        weight_candidates = [
            getattr(self.currentSecondaryCoil, "Weight", None),
        ]
        if isinstance(self.coilData, dict):
            weight_candidates.append(self.coilData.get("Weight"))

        last_error = None
        for weight in weight_candidates:
            if weight is None:
                continue
            try:
                return str(chr(int(float(weight))))
            except (TypeError, ValueError, OverflowError) as e:
                last_error = e

        logger.warning(
            f"{self.id_str} next_code failed, use default code 1: "
            f"{last_error or 'missing weight'}")
        return "1"

    @property
    def next_name(self):
        return infoConfigProperty.get_next(self.next_code)

    @property
    def save_folder(self):
        return Path(self.saveFolder) / str(self.coilId)

    def set_npy_data(self, npy_data):
        array = np.asarray(npy_data)
        if array.ndim != 2 or 0 in array.shape:
            raise ValueError(
                f"invalid stitched 3D data shape: {getattr(array, 'shape', None)}"
            )
        if (not np.issubdtype(array.dtype, np.number)
                or np.issubdtype(array.dtype, np.complexfloating)):
            raise ValueError("stitched 3D data must be real-valued")
        if self.npy_mask is not None and array.shape != self.npy_mask.shape:
            raise ValueError(
                f"stitched 3D/mask shape mismatch: {array.shape} != {self.npy_mask.shape}"
            )
        logger.debug("set_npy_data %s", array.shape)
        invalid = ~np.isfinite(array) | (array < 0)
        if self.npy_mask is not None:
            invalid |= self.npy_mask == 0
        if np.any(invalid):
            array = array.copy()
            array[invalid] = 0
        self.__npyData__ = array
        self._npyData_ = None
        self.__median_non_zero__ = None

    @property
    def circle_config(self):
        if self._circleConfig_ is None:
            self._circleConfig_ = tool.get_circle_config_by_mask(self.npy_mask)
            self.set("width", int(self.width))
            self.set("height", int(self.height))
            self.set("circleConfig", self._circleConfig_)
        return self._circleConfig_

    @property
    def secondary_coil_id(self):
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
        return float(z_value * self.scan3dCoordinateScaleZ +
                     self.scan3dCoordinateOffsetZ)

    def zero_mm(self):
        return self.z_to_mm(0)

    def point_to_mm(self, arr):
        arr = np.array(arr, dtype=float, copy=True)
        arr[:,
            2] = arr[:,
                     2] * self.scan3dCoordinateScaleZ + self.scan3dCoordinateOffsetZ
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
        r1 = cw * r1
        r2 = cw * r2
        center_x, center_y, circlex_radius = self.circle_config[
            "inner_circle"]["circlex"]
        y, x = np.indices(image.shape)
        distance = np.sqrt((x - center_x)**2 + (y - center_y)**2)
        annulus_mask = (distance >= r1) & (distance <= r2)
        if self.npy_mask is not None:
            annulus_mask &= self.npy_mask > 0
        annular_mean_area = np.asarray(image)[annulus_mask]
        annular_mean_area = annular_mean_area[
            np.isfinite(annular_mean_area) & (annular_mean_area > 0)
        ]
        annular_mean = (float(np.median(annular_mean_area))
                        if annular_mean_area.size else float("nan"))
        return annular_mean, annulus_mask

    @property
    def median_non_zero(self):
        if self.__median_non_zero__ is None:
            self.__median_non_zero__, self.annulus_mask = self.annular_region_mean(
                self.__npyData__, 0.6, 0.8)  # 获取平均值
            if np.isnan(self.__median_non_zero__):
                valid = np.isfinite(self.__npyData__) & (self.__npyData__ > 0)
                if self.npy_mask is not None:
                    valid &= self.npy_mask > 0
                nz = self.__npyData__[valid]
                if nz.size:
                    self.__median_non_zero__ = np.median(nz)
                    logger.warning(
                        "%s annular median is NaN, fallback to global median %s",
                        self.key, self.__median_non_zero__)
                else:
                    self.__median_non_zero__ = 0
                    logger.error(
                        "%s annular median is NaN and no non-zero data, fallback to 0",
                        self.key)
        return self.__median_non_zero__

    @property
    def npy_data(self):
        if self._npyData_ is None:
            self._npyData_ = self.__npyData__.copy()
            self.set("median_3d", self.median_non_zero)
            self.set("median_3d_mm", self.median_3d_mm)
        return self._npyData_

    @property
    def median_3d_mm(self):
        # 真实毫米值 = 原始值 * scale + offset
        return self.median_non_zero * self.scan3dCoordinateScaleZ + self.scan3dCoordinateOffsetZ

    def get_bd_xyz(self):
        return [
            self.scan3dCoordinateScaleX, self.scan3dCoordinateScaleY,
            self.scan3dCoordinateScaleZ
        ]

    def set_start(self):
        self.startTime = datetime.datetime.now()
        self.dictData["startTime"] = self.startTime

    def set_original_data(self, datas):
        if not datas:
            raise ValueError("missing camera data for 3D integration")
        self.originalData = datas
        self.bdList = []
        for camera in datas:
            metadata = next((item for item in camera.get("json", [])
                             if isinstance(item, dict) and item.get("bdConfig")
                             and isinstance(item.get("coilData"), dict)), None)
            if metadata is None:
                raise ValueError(
                    f"missing capture metadata for camera {camera.get('camera')}"
                )
            bd_item = BdData(metadata["bdConfig"])
            self.bdList.append(bd_item)
            self.coilData = metadata["coilData"]
            self.use = self.coilData.get("Weight")
            # Retain the historical reference camera. Other camera Z values
            # are converted into these units before stitching.
            for axis, item in (("X", bd_item.bdDataX), ("Y", bd_item.bdDataY),
                               ("Z", bd_item.bdDataZ)):
                scale = float(item.scan3dCoordinateScale)
                offset = float(item.scan3dCoordinateOffset)
                if not np.isfinite(scale) or scale <= 0 or not np.isfinite(offset):
                    raise ValueError(f"invalid camera {camera.get('camera')} {axis} calibration")
                setattr(self, f"scan3dCoordinateScale{axis}", scale)
                setattr(self, f"scan3dCoordinateOffset{axis}", offset)
            self.dictData[
                "scan3dCoordinateScaleX"] = self.scan3dCoordinateScaleX
            self.dictData[
                "scan3dCoordinateScaleY"] = self.scan3dCoordinateScaleY
            self.dictData[
                "scan3dCoordinateScaleZ"] = self.scan3dCoordinateScaleZ
            self.dictData[
                "scan3dCoordinateOffsetX"] = self.scan3dCoordinateOffsetX
            self.dictData[
                "scan3dCoordinateOffsetY"] = self.scan3dCoordinateOffsetY
            self.dictData[
                "scan3dCoordinateOffsetZ"] = self.scan3dCoordinateOffsetZ

    def set_datas(self, datas):
        self.datas = datas

    def set_cross_points(self, cross_points):
        self.crossPoints = cross_points
        self.dictData["crossPoints"] = cross_points

    def get_datas_info(self, datas):

        def get_shape_list(datas_):
            shape_list = []
            for data in datas_:
                shape_list.append(data['2D'].shape)
            return shape_list

        return {
            "cameraLen": len(datas),  # 摄像头数量
            "shapeList": get_shape_list(datas),
            "startTime": self.startTime,
            "crossPoints": self.crossPoints,  # 裁剪数据
        }

    def set(self, key, value):
        logger.debug("%s set -> %s : %s", self.surface, key, value)
        self.dictData[key] = value
        self.__dict__[key] = value

    @property
    def upper_limit(self):
        self.dictData[
            "upperLimit"] = control.upper_limit / self.scan3dCoordinateScaleZ
        return self.dictData["upperLimit"]

    @property
    def lower_limit(self):
        self.dictData[
            "lowerLimit"] = control.lower_limit / self.scan3dCoordinateScaleZ
        return self.dictData["lowerLimit"]

    def set_telescoped_alarms(self):
        mask = self.npy_mask
        mask_area = np.count_nonzero(mask)
        if mask_area <= 0:
            logger.warning("%s telescoped alarm skipped: empty mask area",
                           self.key)
            self.set("lowerArea", 0)
            self.set("upperArea", 0)
            self.set("lowerArea_percent", 0.0)
            self.set("upperArea_percent", 0.0)
            self.set("mask_area", 0)
            return
        npy_area = self.npy_data[mask > 0]
        lower = npy_area[npy_area < (self.__median_non_zero__ +
                                     self.lower_limit)]
        upper = npy_area[npy_area > (self.__median_non_zero__ +
                                     self.upper_limit)]
        lower_area = np.count_nonzero(lower)
        upper_area = np.count_nonzero(upper)
        self.set("lowerArea", lower_area)
        self.set("upperArea", upper_area)
        lower_area_percent = lower_area / mask_area
        upper_area_percent = upper_area / mask_area
        self.set("lowerArea_percent", lower_area_percent)
        self.set("upperArea_percent", upper_area_percent)
        self.set("mask_area", mask_area)

    def commit(self):
        # 数据提交
        logger.debug("commit")
        logger.debug(self.dictData.get("median_3d"))
        dict_data = self.dictData
        json_data = dict(dict_data)
        start_time = json_data.get("startTime")
        if isinstance(start_time, datetime.datetime):
            json_data["startTime"] = start_time.strftime(
                "%Y-%m-%d %H:%M:%S:%f")
        for k in ["median_3d", "median_3d_mm", "start"]:
            v = json_data.get(k)
            if isinstance(v, (float, np.floating)) and not np.isfinite(v):
                logger.error("%s %s is non-finite, fallback to 0", self.key, k)
                json_data[k] = 0.0
        addCoilState(
            CoilStateDB(
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
                jsonData=str(json.dumps(json_data))))

    def add_server_detection_error(self,
                                   error_msg,
                                   error_type="ServerDetectionError"):
        """
        添加服务器检测错误
        """
        add_server_detection_error(
            ServerDetectionError(secondaryCoilId=self.coilId,
                                 surface=self.key,
                                 errorType=error_type,
                                 msg=error_msg))
        self._hasDetectionError_ = True

    def has_detection_error(self):
        return self._hasDetectionError_

    def __iter__(self):
        return iter(()) if self.isNone() else iter((self,))

    def __next__(self):
        if self.index > 0 or self.isNone():
            self.index = 0
            raise StopIteration
        self.index += 1
        return self

    def flatten_surface_by_rotation(self):
        median_non_zero, annulus_mask = self.annular_region_mean(
            self.__npyData__, 0.6, 0.65)  # 获取平均值
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                "%s flatten_surface_by_rotation input: npy_shape=%s, npy_nz=%s, mask_nz=%s, median=%s",
                self.key,
                self.__npyData__.shape,
                int(np.count_nonzero(self.__npyData__)),
                int(np.count_nonzero(self.npy_mask)),
                median_non_zero,
            )
        if np.isnan(median_non_zero) or np.count_nonzero(
                self.__npyData__) == 0:
            logger.error("%s skip flatten: median is NaN or data all zero",
                         self.key)
            return 0
        try:
            a, b, c, rotated_data, angle_data = FlattenSurface.flatten_surface_by_rotation(
                self.__npyData__, annulus_mask, median_non_zero)
        except ValueError as e:
            logger.error("%s flatten_surface_by_rotation skip: %s", self.key,
                         e)
            return 0
        r_z = int(180 - angle_data['angle_with_z'])
        logger.debug("%s rotation %s %s", self.key, r_z, angle_data)
        self.angleData = angle_data
        # return tool.rotate_around_x_axis(self.__npyData__,r_z)
        return r_z

    def set_defect_dict(self, defect_dict):
        self.defect_dict = defect_dict

    def export_json(self):
        """
        构建保存到 data.json 的概要数据，包含中间计算值和二级卷信息。
        """
        data = dict(self.dictData)
        if isinstance(data.get("startTime"), datetime.datetime):
            data["startTime"] = data["startTime"].strftime(
                "%Y-%m-%d %H:%M:%S:%f")
        data["plane_mean"] = float(self.median_non_zero)
        data["plane_mean_mm"] = float(self.median_3d_mm)
        data["crop_box"] = data.get("crop_box")
        data["crossPoints"] = self.crossPoints
        data["coilData"] = self.coilData
        if self.currentSecondaryCoil is not None:
            sec = self.currentSecondaryCoil
            data["secondary"] = {
                "id":
                getattr(sec, "Id", getattr(sec, "id", None)),
                "coil_id":
                getattr(sec, "CoilId", getattr(sec, "coilId", None)),
                "secondary_coil_id":
                getattr(sec, "SecondaryCoilId",
                        getattr(sec, "secondaryCoilId", None)),
                "weight":
                getattr(sec, "Weight", None),
                "status":
                getattr(sec, "Status", None),
            }
        else:
            data["secondary"] = None
        return data


class DataIntegrationList:
    """
    综合数据- List
    """

    def __init__(self):
        self.index = 0
        self.dataIntegrationList: List[DataIntegration] = []

    def append(self, data_integration: DataIntegration):
        self.dataIntegrationList.append(data_integration)

    def __bool__(self):
        return any(not item.isNone() for item in self.dataIntegrationList)

    def __iter__(self):
        return (item for item in self.dataIntegrationList if not item.isNone())

    def __next__(self):
        if self.index < len(self.dataIntegrationList):
            data_integration = self.dataIntegrationList[self.index]
            self.index += 1
            if data_integration.isNone():
                return self.__next__()
            return data_integration
        else:
            self.index = 0
            raise StopIteration
