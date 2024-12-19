from sqlalchemy import Column, Integer, ForeignKey, String, Float, Text, DateTime, func
from sqlalchemy.orm import relationship

from ._base_ import Base


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
