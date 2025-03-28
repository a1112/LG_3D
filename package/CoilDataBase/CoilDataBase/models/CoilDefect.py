from sqlalchemy import Column, Integer, ForeignKey, String, DateTime, func, Float, Text
from sqlalchemy.orm import relationship

from ._base_ import Base


class CoilDefect(Base):
    """
    缺陷数据
    """
    __tablename__ = 'CoilDefect'
    Id = Column(Integer, primary_key=True, autoincrement=True)
    secondaryCoilId = Column(Integer, ForeignKey('SecondaryCoil.Id'))
    surface = Column(String(2))
    defectClass = Column(Integer)
    defectName = Column(String(10))
    defectStatus = Column(Integer)
    defectTime = Column(DateTime, server_default=func.now())
    defectX = Column(Integer)
    defectY = Column(Integer)
    defectW = Column(Integer)
    defectH = Column(Integer)
    defectSource = Column(Float)
    defectData = Column(Text())  #

    parent = relationship("SecondaryCoil", back_populates="childrenCoilDefect")
    children_defect_check = relationship("DefectCheck", back_populates="parent_defect")