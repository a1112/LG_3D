from sqlalchemy import Column, Integer, ForeignKey, String, Float, Text, DateTime, func
from sqlalchemy.orm import relationship

from CoilDataBase.models._base_ import Base


class TaperShapePoint(Base):
    """
    塔形检测点
    """
    __tablename__ = 'TaperShapePoint'
    Id = Column(Integer, primary_key=True, autoincrement=True)
    secondaryCoilId = Column(Integer, ForeignKey('SecondaryCoil.Id'))
    surface = Column(String(2))
    x = Column(Integer)
    y = Column(Integer)
    value = Column(Float)
    level = Column(Integer)
    err_msg = Column(Text)
    crateTime = Column(DateTime, server_default=func.now())
    data = Column(Text())

    parent = relationship("SecondaryCoil", back_populates="childrenTaperShapePoint")
