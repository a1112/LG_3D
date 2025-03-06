from sqlalchemy import Column, Integer, ForeignKey, String, DateTime, func, Float, Text
from sqlalchemy.orm import relationship

from ._base_ import Base

class CoilCheck(Base):
    __tablename__ = 'CoilCheck'
    Id = Column(Integer, primary_key=True, autoincrement=True)
    secondaryCoilId = Column(Integer, ForeignKey('SecondaryCoil.Id'))

    status = Column(Integer)
    msg = Column(Text)

    parent = relationship("SecondaryCoil", back_populates="childrenCoilCheck")