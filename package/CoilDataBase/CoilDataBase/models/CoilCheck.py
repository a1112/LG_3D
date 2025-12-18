from sqlalchemy import Column, Integer, ForeignKey, String, DateTime, func, Float, Text
from sqlalchemy.orm import relationship

from ._base_ import Base


class CoilCheck(Base):
    __tablename__ = 'CoilCheck'
    Id = Column(Integer, primary_key=True, autoincrement=True, comment="主键")

    secondaryCoilId = Column(Integer, ForeignKey('SecondaryCoil.Id'), comment="关联的二级卷ID")

    status = Column(Integer, comment="校验状态")
    msg = Column(Text, comment="校验信息")

    parent = relationship("SecondaryCoil", back_populates="childrenCoilCheck")
