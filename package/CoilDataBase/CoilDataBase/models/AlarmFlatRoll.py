from sqlalchemy import Column, Integer, ForeignKey, String, Float, Text, DateTime, func
from sqlalchemy.orm import relationship

from CoilDataBase.models._base_ import Base


class AlarmFlatRoll(Base):
    """
    扁卷检测，弃用，下版本中移除该数据结构
    """
    __tablename__ = 'AlarmFlatRoll'
    Id = Column(Integer, primary_key=True, autoincrement=True)
    secondaryCoilId = Column(Integer, ForeignKey('SecondaryCoil.Id'))
    surface = Column(String(2))
    out_circle_width = Column(Float)
    out_circle_height = Column(Float)
    out_circle_center_x = Column(Float)
    out_circle_center_y = Column(Float)
    out_circle_radius = Column(Float)
    inner_circle_width = Column(Float)
    inner_circle_height = Column(Float)
    inner_circle_center_x = Column(Float)
    inner_circle_center_y = Column(Float)
    inner_circle_radius = Column(Float)
    accuracy_x = Column(Float)
    accuracy_y = Column(Float)
    level = Column(Integer)
    err_msg = Column(Text)
    crateTime = Column(DateTime, server_default=func.now())
    data = Column(Text())

    parent = relationship("SecondaryCoil", back_populates="childrenAlarmFlatRoll")
