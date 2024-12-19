from sqlalchemy import Column, Integer, ForeignKey, String, DateTime, func, Text
from sqlalchemy.orm import relationship

from CoilDataBase.models._base_ import Base


class ServerDetectionError(Base):
    __tablename__ = 'ServerDetectionError'
    Id = Column(Integer, primary_key=True, autoincrement=True)
    secondaryCoilId = Column(Integer, ForeignKey('SecondaryCoil.Id'))
    surface = Column(String(2))
    errorType = Column(String(20))
    time = Column(DateTime, server_default=func.now())
    msg = Column(Text)
    parent = relationship("SecondaryCoil", back_populates="childrenServerDetectionError")
