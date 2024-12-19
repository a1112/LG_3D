from sqlalchemy import Column, Integer, ForeignKey, String, Float, Text, DateTime, func
from sqlalchemy.orm import relationship

from ._base_ import Base


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
