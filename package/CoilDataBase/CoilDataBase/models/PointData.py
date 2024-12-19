from sqlalchemy import Column, Integer, ForeignKey, String, Float, Text, DateTime, func
from sqlalchemy.orm import relationship

from CoilDataBase.models._base_ import Base


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
