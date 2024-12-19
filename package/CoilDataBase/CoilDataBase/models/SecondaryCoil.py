from sqlalchemy import Column, Integer, String, Float, DateTime, func
from sqlalchemy.orm import relationship

from ._base_ import Base


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

    def get_json(self):
        return {
            "Id": self.Id,
            "CoilNo": self.CoilNo,
            "CoilType": self.CoilType,
            "CoilInside": self.CoilInside,
            "CoilDia": self.CoilDia,
            "Thickness": self.Thickness,
            "Width": self.Width,
            "Weight": self.Weight,
            "ActWidth": self.ActWidth,
            # "CreateTime": self.CreateTime
        }

    def __repr__(self):
        return self.get_json().__repr__()

    def __str__(self):
        return self.get_json().__str__()
