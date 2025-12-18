from sqlalchemy import Column, Integer, ForeignKey, String, DateTime, func, Float
from sqlalchemy.orm import relationship

from ._base_ import Base


class DetectionSpeed(Base):
    """
    检测速度
    """
    __tablename__ = 'DetectionSpeed'
    Id = Column(Integer, primary_key=True, autoincrement=True, comment="主键")
    secondaryCoilId = Column(Integer, ForeignKey('SecondaryCoil.Id'), comment="关联的二级卷ID")
    surface = Column(String(2), comment="表面标识（S/L）")
    startTime = Column(DateTime, server_default=func.now(), comment="开始时间")
    endTime = Column(DateTime, server_default=func.now(), comment="结束时间")
    allTime = Column(Float, comment="总用时")

    parent = relationship("SecondaryCoil", back_populates="childrenDetectionSpeed")
