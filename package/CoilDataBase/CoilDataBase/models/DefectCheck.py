from sqlalchemy import Column, Integer, ForeignKey, String, DateTime, func, Float, Text
from sqlalchemy.orm import relationship

from ._base_ import Base


class DefectCheck(Base):
    __tablename__ = 'DefectCheck'
    Id = Column(Integer, primary_key=True, autoincrement=True)

    secondaryCoilId = Column(Integer, ForeignKey('SecondaryCoil.Id'))
    defectId = Column(Integer, ForeignKey('CoilDefect.Id'))
    key = Column(String(5))
    status = Column(Integer)
    oldDefectId = Column(Integer)
    oldDefectName = Column(String(10))
    newDefectId = Column(Integer)
    newDefectName = Column(String(10))
    addTime = Column(DateTime)
    msg = Column(Text)


    # parent = relationship("SecondaryCoil", back_populates="childrenDefectCheck")