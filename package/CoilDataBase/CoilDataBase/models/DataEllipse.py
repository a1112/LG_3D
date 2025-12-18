from sqlalchemy import Column, Integer, ForeignKey, String, Float, Text, DateTime, func
from sqlalchemy.orm import relationship

from ._base_ import Base


class DataEllipse(Base):
    __tablename__ = 'DataEllipse'
    Id = Column(Integer, primary_key=True, autoincrement=True, comment="主键")
    secondaryCoilId = Column(Integer, ForeignKey('SecondaryCoil.Id'), comment="关联的二级卷ID")
    surface = Column(String(2), comment="表面标识（S/L）")

    type = Column(String(10), comment="椭圆类型")
    center_x = Column(Float, comment="中心X")
    center_y = Column(Float, comment="中心Y")
    width = Column(Float, comment="宽")
    height = Column(Float, comment="高")
    rotation_angle = Column(Float, comment="旋转角度")

    level = Column(Integer, comment="报警等级")
    err_msg = Column(Text, comment="报警信息")
    crateTime = Column(DateTime, server_default=func.now(), comment="创建时间")
    data = Column(Text, comment="检测数据")
    parent = relationship("SecondaryCoil", back_populates="childrenDataEllipse")
