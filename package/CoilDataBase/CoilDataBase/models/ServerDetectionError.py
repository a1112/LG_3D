from sqlalchemy import Column, Integer, ForeignKey, String, DateTime, func, Text
from sqlalchemy.orm import relationship

from ._base_ import Base

class ServerDetectionError(Base):
    __tablename__ = 'ServerDetectionError'
    Id = Column(Integer, primary_key=True, autoincrement=True, comment="主键")
    secondaryCoilId = Column(Integer, ForeignKey('SecondaryCoil.Id'), comment="关联的二级卷ID")
    surface = Column(String(2), comment="表面标识（S/L）")
    errorType = Column(String(20), comment="错误类型")
    time = Column(DateTime, server_default=func.now(), comment="错误时间")
    msg = Column(Text, comment="错误信息")
    parent = relationship("SecondaryCoil", back_populates="childrenServerDetectionError")
