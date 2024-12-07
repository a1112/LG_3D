import datetime

from sqlalchemy import Column, Integer, String, DateTime, Float, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()


class SecondaryCoil(Base):
    """
    二级数据
    """
    __tablename__ = 'SecondaryCoil'
    #   extend_existing=True
    Id = Column(Integer, primary_key=True, autoincrement=True)
    CoilNo = Column(String(20))
    CoilType = Column(String(20))
    CoilInside = Column(Float)  # 内径
    CoilDia = Column(Float)  # 卷径
    Thickness = Column(Float)
    Width = Column(Float)
    Weight = Column(Float)
    ActWidth = Column(Float)
    CreateTime = Column(DateTime, server_default=func.now())

    childrenCoil = relationship("Coil", back_populates="parent")
    childrenCoilState = relationship("CoilState", back_populates="parent")
    childrenCoilDefect = relationship("CoilDefect", back_populates="parent")
    childrenCoilAlarmStatus = relationship("CoilAlarmStatus", back_populates="parent")
    childrenAlarmFlatRoll = relationship("AlarmFlatRoll", back_populates="parent")
    childrenTaperShapePoint = relationship("TaperShapePoint", back_populates="parent")
    childrenAlarmInfo = relationship("AlarmInfo", back_populates="parent")
    childrenPlcData = relationship("PlcData", back_populates="parent")
    childrenAlarmTaperShape = relationship("AlarmTaperShape", back_populates="parent")
    childrenAlarmLooseCoil = relationship("AlarmLooseCoil", back_populates="parent")
    childrenDetectionSpeed = relationship("DetectionSpeed", back_populates="parent")
    childrenServerDetectionError = relationship("ServerDetectionError", back_populates="parent")

    childrenDataEllipse = relationship("DataEllipse", back_populates="parent")

    childrenLineData = relationship("LineData", back_populates="parent")
    childrenPointData = relationship("PointData", back_populates="parent")
    childrenAlarmFlatRollData = relationship("AlarmFlatRollData", back_populates="parent")


class Coil(Base):
    """
    检测数据

    """
    __tablename__ = 'Coil'
    Id = Column(Integer, primary_key=True, autoincrement=True)
    SecondaryCoilId = Column(Integer, ForeignKey('SecondaryCoil.Id'))
    DetectionTime = Column(DateTime, server_default=func.now())
    DefectCountS = Column(Integer)
    DefectCountL = Column(Integer)
    CheckStatus = Column(Integer)
    Status_L = Column(Integer)
    Status_S = Column(Integer)
    Grade = Column(Integer)
    Msg = Column(Text())

    parent = relationship("SecondaryCoil", back_populates="childrenCoil")


class CoilState(Base):
    """状态数据"""
    __tablename__ = 'CoilState'
    Id = Column(Integer, primary_key=True, autoincrement=True)
    secondaryCoilId = Column(Integer, ForeignKey('SecondaryCoil.Id'))
    surface = Column(String(2))
    startTime = Column(DateTime, server_default=func.now())
    scan3dCoordinateScaleX = Column(Float)
    scan3dCoordinateScaleY = Column(Float)
    scan3dCoordinateScaleZ = Column(Float)
    rotate = Column(Integer)
    x_rotate = Column(Integer)
    median_3d = Column(Float)
    median_3d_mm = Column(Float)
    colorFromValue_mm = Column(Float)
    colorToValue_mm = Column(Float)
    start = Column(Float)
    step = Column(Float)
    upperLimit = Column(Float)
    lowerLimit = Column(Float)
    lowerArea = Column(Integer)
    upperArea = Column(Integer)
    lowerArea_percent = Column(Float)
    upperArea_percent = Column(Float)
    mask_area = Column(Integer)
    width = Column(Integer)
    height = Column(Integer)
    jsonData = Column(Text())  #

    parent = relationship("SecondaryCoil", back_populates="childrenCoilState")


class CoilDefect(Base):
    """
    缺陷数据
    """
    __tablename__ = 'CoilDefect'
    Id = Column(Integer, primary_key=True, autoincrement=True)
    secondaryCoilId = Column(Integer, ForeignKey('SecondaryCoil.Id'))
    surface = Column(String(2))
    defectClass = Column(Integer)
    defectName = Column(String(10))
    defectStatus = Column(Integer)
    defectTime = Column(DateTime, server_default=func.now())
    defectX = Column(Integer)
    defectY = Column(Integer)
    defectW = Column(Integer)
    defectH = Column(Integer)
    defectSource = Column(Float)
    defectData = Column(Text())  #

    parent = relationship("SecondaryCoil", back_populates="childrenCoilDefect")


class DefectClassDict(Base):
    """
    缺陷类别数据
    """
    __tablename__ = 'DefectClassDict'
    Id = Column(Integer, primary_key=True, autoincrement=True)
    defectClass = Column(Integer)
    defectName = Column(String(10))
    defectType = Column(String(10))
    defectColor = Column(String(10))
    defectLevel = Column(Integer)
    visible = Column(Integer)
    defectDesc = Column(Text())


class PlcData(Base):
    """
    PLC  数据

    """
    __tablename__ = 'PlcData'
    Id = Column(Integer, primary_key=True, autoincrement=True)
    secondaryCoilId = Column(Integer, ForeignKey('SecondaryCoil.Id'))
    location_S = Column(Float)
    location_L = Column(Float)
    location_laser = Column(Float)
    startTime = Column(DateTime, server_default=func.now())
    pclData = Column(Text)

    parent = relationship("SecondaryCoil", back_populates="childrenPlcData")


class CoilAlarmStatus(Base):
    """报警数据"""
    __tablename__ = 'CoilAlarmStatus'
    Id = Column(Integer, primary_key=True, autoincrement=True)
    secondaryCoilId = Column(Integer, ForeignKey('SecondaryCoil.Id'))
    surface = Column(String(2))
    level = Column(Integer)
    alarmStatus = Column(Integer)
    alarmFlatRoll = Column(Integer)
    alarmTaper = Column(Integer)
    alarmFolding = Column(Integer)
    alarmDefect = Column(Integer)
    crateTime = Column(DateTime, server_default=func.now())
    data = Column(Text())
    parent = relationship("SecondaryCoil", back_populates="childrenCoilAlarmStatus")


class AlarmFlatRoll(Base):
    """
    扁卷检测
    """
    __tablename__ = 'AlarmFlatRoll'
    Id = Column(Integer, primary_key=True, autoincrement=True)
    secondaryCoilId = Column(Integer, ForeignKey('SecondaryCoil.Id'))
    surface = Column(String(2))
    out_circle_width = Column(Float)
    out_circle_height = Column(Float)
    out_circle_center_x = Column(Float)
    out_circle_center_y = Column(Float)
    out_circle_radius = Column(Float)
    inner_circle_width = Column(Float)
    inner_circle_height = Column(Float)
    inner_circle_center_x = Column(Float)
    inner_circle_center_y = Column(Float)
    inner_circle_radius = Column(Float)
    accuracy_x = Column(Float)
    accuracy_y = Column(Float)
    level = Column(Integer)
    err_msg = Column(Text)
    crateTime = Column(DateTime, server_default=func.now())
    data = Column(Text())

    parent = relationship("SecondaryCoil", back_populates="childrenAlarmFlatRoll")


class TaperShapePoint(Base):
    """
    塔形检测点
    """
    __tablename__ = 'TaperShapePoint'
    Id = Column(Integer, primary_key=True, autoincrement=True)
    secondaryCoilId = Column(Integer, ForeignKey('SecondaryCoil.Id'))
    surface = Column(String(2))
    x = Column(Integer)
    y = Column(Integer)
    value = Column(Float)
    level = Column(Integer)
    err_msg = Column(Text)
    crateTime = Column(DateTime, server_default=func.now())
    data = Column(Text())

    parent = relationship("SecondaryCoil", back_populates="childrenTaperShapePoint")


class DeepPoint(Base):
    """
    深度点
    """
    __tablename__ = 'DeepPoint'
    Id = Column(Integer, primary_key=True, autoincrement=True)
    secondaryCoilId = Column(Integer, ForeignKey('SecondaryCoil.Id'))
    surface = Column(String(2))
    x = Column(Integer)
    y = Column(Integer)
    x_mm = Column(Float)
    y_mm = Column(Float)
    value = Column(Float)
    value_int = Column(Integer)
    by_user = Column(Integer)
    draw = Column(Integer)
    level = Column(Integer)
    err_msg = Column(Text)
    crateTime = Column(DateTime, server_default=func.now())
    data = Column(Text())


class AlarmTaperShape(Base):
    """
    塔形检测
    """
    __tablename__ = 'AlarmTaperShape'
    Id = Column(Integer, primary_key=True, autoincrement=True)
    secondaryCoilId = Column(Integer, ForeignKey('SecondaryCoil.Id'))
    surface = Column(String(2))
    out_taper_max_x = Column(Integer)
    out_taper_max_y = Column(Integer)
    out_taper_max_value = Column(Float)
    out_taper_min_x = Column(Integer)
    out_taper_min_y = Column(Integer)
    out_taper_min_value = Column(Float)

    in_taper_max_x = Column(Integer)
    in_taper_max_y = Column(Integer)
    in_taper_max_value = Column(Float)
    in_taper_min_x = Column(Integer)
    in_taper_min_y = Column(Integer)
    in_taper_min_value = Column(Float)

    rotation_angle = Column(Float)

    level = Column(Integer)
    err_msg = Column(Text)
    crateTime = Column(DateTime, server_default=func.now())
    data = Column(Text())

    parent = relationship("SecondaryCoil", back_populates="childrenAlarmTaperShape")


class AlarmLooseCoil(Base):
    """
    松卷
    """
    __tablename__ = 'AlarmLooseCoil'
    Id = Column(Integer, primary_key=True, autoincrement=True)
    secondaryCoilId = Column(Integer, ForeignKey('SecondaryCoil.Id'))
    surface = Column(String(2))
    max_width = Column(Float)

    rotation_angle = Column(Float)

    level = Column(Integer)
    err_msg = Column(Text)
    crateTime = Column(DateTime, server_default=func.now())
    data = Column(Text())

    parent = relationship("SecondaryCoil", back_populates="childrenAlarmLooseCoil")


class DetectionSpeed(Base):
    """
    检测速度
    """
    __tablename__ = 'DetectionSpeed'
    Id = Column(Integer, primary_key=True, autoincrement=True)
    secondaryCoilId = Column(Integer, ForeignKey('SecondaryCoil.Id'))
    surface = Column(String(2))
    startTime = Column(DateTime, server_default=func.now())
    endTime = Column(DateTime, server_default=func.now())
    allTime = Column(Float)

    parent = relationship("SecondaryCoil", back_populates="childrenDetectionSpeed")


class NextCodeDict(Base):
    """
    下一工序
    """
    __tablename__ = 'NextCodeDict'
    Id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(2))
    info = Column(Text)


class AlarmInfo(Base):
    """
    报警表
    """
    __tablename__ = 'AlarmInfo'
    Id = Column(Integer, primary_key=True, autoincrement=True)
    secondaryCoilId = Column(Integer, ForeignKey('SecondaryCoil.Id'))
    surface = Column(String(2))
    nextCode = Column(String(2))
    nextName = Column(String(10))

    taperShapeGrad = Column(Integer)  # 塔形检测  报警等级
    taperShapeMsg = Column(Text)  # 塔形检测  报警信息

    looseCoilGrad = Column(Integer)  # 松卷检测  报警等级
    looseCoilMsg = Column(Text)  # 松卷检测  报警等级

    flatRollGrad = Column(Integer)  # 扁卷检测  报警等级
    flatRollMsg = Column(Text)  # 扁卷检测  报警等级

    defectGrad = Column(Integer)  # 缺陷检测  报警等级
    defectMsg = Column(Text)  # 缺陷检测  报警等级

    grad = Column(Integer)  # 综合  报警等级
    crateTime = Column(DateTime, server_default=func.now())
    data = Column(Text())  # 综合  报警数据

    parent = relationship("SecondaryCoil", back_populates="childrenAlarmInfo")


class CapTrueLog(Base):
    """
    记录采集日志
    """
    __tablename__ = 'CapTrueLog'
    Id = Column(Integer, primary_key=True, autoincrement=True)
    secondaryCoilId = Column(Integer, ForeignKey('SecondaryCoil.Id'))
    cameraId = Column(Integer)
    cameraName = Column(String(10))
    capTrueStartTime = Column(DateTime, server_default=func.now())
    capTrueEndTime = Column(DateTime, server_default=func.now())


class ServerDetectionError(Base):
    __tablename__ = 'ServerDetectionError'
    Id = Column(Integer, primary_key=True, autoincrement=True)
    secondaryCoilId = Column(Integer, ForeignKey('SecondaryCoil.Id'))
    surface = Column(String(2))
    errorType = Column(String(20))
    time = Column(DateTime, server_default=func.now())
    msg = Column(Text)
    parent = relationship("SecondaryCoil", back_populates="childrenServerDetectionError")


class DataEllipse(Base):
    __tablename__ = 'DataEllipse'
    Id = Column(Integer, primary_key=True, autoincrement=True)
    secondaryCoilId = Column(Integer, ForeignKey('SecondaryCoil.Id'))
    surface = Column(String(2))

    type = Column(String(10))
    center_x = Column(Float)
    center_y = Column(Float)
    width = Column(Float)
    height = Column(Float)
    rotation_angle = Column(Float)

    level = Column(Integer)
    err_msg = Column(Text)
    crateTime = Column(DateTime, server_default=func.now())
    data = Column(Text)
    parent = relationship("SecondaryCoil", back_populates="childrenDataEllipse")


class AlarmFlatRollData(Base):
    __tablename__ = 'AlarmFlatRollData'
    Id = Column(Integer, primary_key=True, autoincrement=True)
    secondaryCoilId = Column(Integer, ForeignKey('SecondaryCoil.Id'))
    surface = Column(String(2))
    level = Column(Integer)
    err_msg = Column(Text)
    crateTime = Column(DateTime, server_default=func.now())
    data = Column(Text)
    parent = relationship("SecondaryCoil", back_populates="childrenAlarmFlatRollData")


class LineData(Base):
    __tablename__ = 'LineData'
    Id = Column(Integer, primary_key=True, autoincrement=True)
    secondaryCoilId = Column(Integer, ForeignKey('SecondaryCoil.Id'))
    surface = Column(String(2))
    type = Column(String(20))
    center_x = Column(Float)
    center_y = Column(Float)
    width = Column(Float)
    height = Column(Float)
    rotation_angle = Column(Float)
    x1 = Column(Float)
    y1 = Column(Float)
    x2 = Column(Float)
    y2 = Column(Float)
    data = Column(Text)
    inner_min_value = Column(Float)
    inner_min_value_mm = Column(Float)
    inner_max_value = Column(Float)
    inner_max_value_mm = Column(Float)
    outer_min_value = Column(Float)
    outer_min_value_mm = Column(Float)
    outer_max_value = Column(Float)
    outer_max_value_mm = Column(Float)
    crateTime = Column(DateTime, server_default=func.now())

    parent = relationship("SecondaryCoil", back_populates="childrenLineData")


class PointData(Base):
    __tablename__ = 'PointData'
    Id = Column(Integer, primary_key=True, autoincrement=True)
    secondaryCoilId = Column(Integer, ForeignKey('SecondaryCoil.Id'))
    surface = Column(String(2))
    type = Column(String(10))
    x = Column(Float)
    y = Column(Float)
    z = Column(Float)
    z_mm = Column(Float)
    data = Column(Text)

    crateTime = Column(DateTime, server_default=func.now())

    parent = relationship("SecondaryCoil", back_populates="childrenPointData")
