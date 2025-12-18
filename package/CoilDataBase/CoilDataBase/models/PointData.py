from sqlalchemy import Column, Integer, ForeignKey, String, Float, Text, DateTime, func
from sqlalchemy.orm import relationship

from ._base_ import Base


class PointData(Base):
    __tablename__ = 'PointData'
    Id = Column(Integer, primary_key=True, autoincrement=True, comment="主键")
    secondaryCoilId = Column(Integer, ForeignKey('SecondaryCoil.Id'), comment="关联的二级卷ID")
    surface = Column(String(2), comment="表面标识（S/L）")
    type = Column(String(10), comment="点类型")
    x = Column(Float, comment="X坐标")
    y = Column(Float, comment="Y坐标")
    z = Column(Float, comment="Z值")
    z_mm = Column(Float, comment="Z值（毫米）")
    data = Column(Text, comment="点数据")

    crateTime = Column(DateTime, server_default=func.now(), comment="创建时间")

    parent = relationship("SecondaryCoil", back_populates="childrenPointData")
