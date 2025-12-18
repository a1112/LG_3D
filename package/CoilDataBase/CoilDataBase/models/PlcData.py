from sqlalchemy import Column, Integer, ForeignKey, Float, DateTime, func, Text
from sqlalchemy.orm import relationship

from ._base_ import Base


class PlcData(Base):
    """
    PLC 数据
    """
    __tablename__ = 'PlcData'
    Id = Column(Integer, primary_key=True, autoincrement=True, comment="主键")
    secondaryCoilId = Column(Integer, ForeignKey('SecondaryCoil.Id'), comment="关联的二级卷ID")
    location_S = Column(Float, comment="短边位置")
    location_L = Column(Float, comment="长边位置")
    location_laser = Column(Float, comment="激光位置")
    startTime = Column(DateTime, server_default=func.now(), comment="开始时间")
    pclData = Column(Text, comment="PLC 数据内容")

    parent = relationship("SecondaryCoil", back_populates="childrenPlcData")
