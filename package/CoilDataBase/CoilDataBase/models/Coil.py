from sqlalchemy import Column, Integer, ForeignKey, DateTime, func, Text
from sqlalchemy.orm import relationship

from CoilDataBase.models._base_ import Base


class Coil(Base):
    """
    检测数据

    """
    __tablename__ = 'Coil'
    Id = Column(Integer, primary_key=True, autoincrement=True)
    SecondaryCoilId = Column(Integer, ForeignKey('SecondaryCoil.Id'))
    DetectionTime = Column(DateTime, server_default=func.now())
    DefectCountS = Column(Integer)
    DefectCountL = Column(Integer)
    CheckStatus = Column(Integer)
    Status_L = Column(Integer)
    Status_S = Column(Integer)
    Grade = Column(Integer)
    Msg = Column(Text())

    parent = relationship("SecondaryCoil", back_populates="childrenCoil")
