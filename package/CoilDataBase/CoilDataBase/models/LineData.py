from sqlalchemy import Column, Integer, ForeignKey, String, Float, Text, DateTime, func
from sqlalchemy.orm import relationship

from ._base_ import Base


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
