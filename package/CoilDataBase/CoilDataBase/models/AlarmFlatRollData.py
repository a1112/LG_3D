from sqlalchemy import Column, Integer, ForeignKey, String, Text, DateTime, func
from sqlalchemy.orm import relationship

from ._base_ import Base


class AlarmFlatRollData(Base):
    __tablename__ = 'AlarmFlatRollData'
    Id = Column(Integer, primary_key=True, autoincrement=True)
    secondaryCoilId = Column(Integer, ForeignKey('SecondaryCoil.Id'))
    surface = Column(String(2))
    level = Column(Integer)
    err_msg = Column(Text)
    crateTime = Column(DateTime, server_default=func.now())
    data = Column(Text)
    parent = relationship("SecondaryCoil", back_populates="childrenAlarmFlatRollData")
