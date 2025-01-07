from sqlalchemy import Column, Integer, ForeignKey, String, loat, Text, DateTime, func
from sqlalchemy.orm import relationship
from ._base_ import Base

class DefectStatistics(Base):
    """
    甲方需求的缺陷的总体汇报
    """
    __tablename__ = 'DefectStatistics'
    Id = Column(Integer, primary_key=True, autoincrement=True)
    secondaryCoilId = Column(Integer, ForeignKey('SecondaryCoil.Id'))
    surface = Column(String(2))


    parent = relationship("SecondaryCoil", back_populates="childrenDefectStatistics")