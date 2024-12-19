from sqlalchemy import Column, Integer, ForeignKey, String, DateTime, func, Text
from sqlalchemy.orm import relationship

from CoilDataBase.models._base_ import Base


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
