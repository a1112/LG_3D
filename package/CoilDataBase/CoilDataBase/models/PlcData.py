from sqlalchemy import Column, Integer, ForeignKey, Float, DateTime, func, Text
from sqlalchemy.orm import relationship

from CoilDataBase.models._base_ import Base


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
