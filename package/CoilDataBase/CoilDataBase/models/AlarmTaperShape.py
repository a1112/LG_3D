from sqlalchemy import Column, Integer, ForeignKey, String, Float, Text, DateTime, func
from sqlalchemy.orm import relationship

from ._base_ import Base


class AlarmTaperShape(Base):
    """
    塔形检测
    """
    __tablename__ = 'AlarmTaperShape'
    Id = Column(Integer, primary_key=True, autoincrement=True)
    secondaryCoilId = Column(Integer, ForeignKey('SecondaryCoil.Id'))
    surface = Column(String(2))
    out_taper_max_x = Column(Integer)
    out_taper_max_y = Column(Integer)
    out_taper_max_value = Column(Float)
    out_taper_min_x = Column(Integer)
    out_taper_min_y = Column(Integer)
    out_taper_min_value = Column(Float)

    in_taper_max_x = Column(Integer)
    in_taper_max_y = Column(Integer)
    in_taper_max_value = Column(Float)
    in_taper_min_x = Column(Integer)
    in_taper_min_y = Column(Integer)
    in_taper_min_value = Column(Float)

    rotation_angle = Column(Float)

    level = Column(Integer)
    err_msg = Column(Text)
    crateTime = Column(DateTime, server_default=func.now())
    data = Column(Text())

    parent = relationship("SecondaryCoil", back_populates="childrenAlarmTaperShape")
