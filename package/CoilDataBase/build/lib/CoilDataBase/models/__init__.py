import datetime

from sqlalchemy import Column, Integer, String, DateTime, Float, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
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


class Coil(Base):
    """
    检测数据

    """
    __tablename__ = 'Coil'
    Id = Column(Integer, primary_key=True, autoincrement=True)
    SecondaryCoilId = Column(Integer,ForeignKey('SecondaryCoil.Id'))
    DetectionTime = Column(DateTime, server_default=func.now())
    DefectCountS = Column(Integer)
    DefectCountL = Column(Integer)
    CheckStatus = Column(Integer)
    Status_L = Column(Integer)
    Status_S = Column(Integer)
    Grade = Column(Integer)
    Msg = Column(Text())


class CoilState(Base):
    """状态数据"""
    __tablename__ = 'CoilState'
    Id = Column(Integer, primary_key=True, autoincrement=True)
    secondaryCoilId = Column(Integer,ForeignKey('SecondaryCoil.Id'))
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


class CoilDefect(Base):
    """
    缺陷数据

    """
    __tablename__ = 'CoilDefect'
    Id = Column(Integer, primary_key=True, autoincrement=True)
    secondaryCoilId = Column(Integer)
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
    secondaryCoilId = Column(Integer)
    location_S = Column(Float)
    location_L = Column(Float)
    location_laser = Column(Float)
    startTime = Column(DateTime, server_default=func.now())
    pclData = Column(Text)

class  CoilAlarmStatus(Base):
    """报警数据"""
    __tablename__ = 'CoilAlarmStatus'
    Id = Column(Integer, primary_key=True, autoincrement=True)
    secondaryCoilId = Column(Integer)
    surface = Column(String(2))
    level = Column(Integer)
    alarmStatus = Column(Integer)
    alarmFlatRoll = Column(Integer)
    alarmTaper = Column(Integer)
    alarmFolding = Column(Integer)
    alarmDefect = Column(Integer)
    crateTime = Column(DateTime, server_default=func.now())
    data = Column(Text())

class AlarmFlatRoll(Base):
    __tablename__ = 'AlarmFlatRoll'
    Id = Column(Integer, primary_key=True, autoincrement=True)
    secondaryCoilId = Column(Integer)
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


class TaperShapePoint(Base):
    __tablename__ = 'TaperShapePoint'
    Id = Column(Integer, primary_key=True, autoincrement=True)
    secondaryCoilId = Column(Integer)
    surface = Column(String(2))
    x = Column(Integer)
    y = Column(Integer)
    value = Column(Float)
    level = Column(Integer)
    err_msg = Column(Text)
    crateTime = Column(DateTime, server_default=func.now())
    data = Column(Text())

class AlarmTaperShape(Base):
    __tablename__ = 'AlarmTaperShape'
    Id = Column(Integer, primary_key=True, autoincrement=True)
    secondaryCoilId = Column(Integer)
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

class AlarmLooseCoil(Base):
    __tablename__ = 'AlarmLooseCoil'
    Id = Column(Integer, primary_key=True, autoincrement=True)
    secondaryCoilId = Column(Integer)
    surface = Column(String(2))
    max_width = Column(Float)

    rotation_angle = Column(Float)

    level = Column(Integer)
    err_msg = Column(Text)
    crateTime = Column(DateTime, server_default=func.now())
    data = Column(Text())

class DetectionSpeed(Base):
    __tablename__ = 'DetectionSpeed'
    Id = Column(Integer, primary_key=True, autoincrement=True)
    secondaryCoilId = Column(Integer)
    surface = Column(String(2))
    startTime = Column(DateTime, server_default=func.now())
    endTime = Column(DateTime, server_default=func.now())
    allTime = Column(Float)

class NextCodeDict(Base):
    __tablename__ = 'NextCodeDict'
    Id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(2))
    info = Column(Text)


t={'coilId': '6554',
   'direction': 'R',
   'startTime': datetime.datetime(2024, 8, 16, 14, 8, 38, 301792),
   'scan3dCoordinateScaleX': 0.3415023386478424,
   'scan3dCoordinateScaleY': 1.0, 'scan3dCoordinateScaleZ': 0.01680760271847248,
   'crossPoints': [(2313, 60), (2311, 65)], 'rotate': -90, 'crop_box': (0, 1430, 5932, 5459),
   'x_rotate': 10, 'median_3d': 42575.23971781661, 'median_3d_mm': 690.9751332314569,
   'colorFromValue_mm': -20, 'colorToValue_mm': 20, 'start': 41342.23971781661, 'step': 2465.0,
   'upperLimit': 5949.688463905355, 'lowerLimit': -5949.688463905355, 'lowerArea': 96031, 'upperArea': 2085,
   'lowerArea_percent': 0.004192965026328996, 'upperArea_percent': 9.103656194245564e-05, 'mask_area': 22902886,
   'width': 5932, 'height': 5459, 'circleConfig': {'inner_circle': {'circlex': [2950, 2993, 1140],
                                                                    'ellipse': ((2959.546142578125, 2979.77978515625),
                                                                                (2215.0205078125, 2247.829833984375),
                                                                                71.07267761230469),
    'inner_circle': [(2939.515380859375, 2977.1162109375), 1108.7459716796875]}}}


# class AlarmSettings(Base):
#     __tablename__ = 'AlarmSettings'
#     Id = Column(Integer, primary_key=True, autoincrement=True)
#     SecondaryCoilId = Column(Integer,ForeignKey('SecondaryCoil.Id'))
#     alarmType = Column(String(20))
#     alarmValue = Column(Float)
#     alarmStatus = Column(Integer)
#     alarmTime = Column(DateTime, server_default=func.now())
#     alarmData = Column(Text())  # 报警数据