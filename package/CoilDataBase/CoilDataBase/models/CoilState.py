from ._base_ import *


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
