from sqlalchemy import Column, Integer, ForeignKey, String, DateTime, func, Float
from sqlalchemy.orm import relationship

from CoilDataBase.models._base_ import Base


class DetectionSpeed(Base):
    """
    检测速度
    """
    __tablename__ = 'DetectionSpeed'
    Id = Column(Integer, primary_key=True, autoincrement=True)
    secondaryCoilId = Column(Integer, ForeignKey('SecondaryCoil.Id'))
    surface = Column(String(2))
    startTime = Column(DateTime, server_default=func.now())
    endTime = Column(DateTime, server_default=func.now())
    allTime = Column(Float)

    parent = relationship("SecondaryCoil", back_populates="childrenDetectionSpeed")
