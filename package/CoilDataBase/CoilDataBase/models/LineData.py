from sqlalchemy import Column, Integer, ForeignKey, String, Float, Text, DateTime, func
from sqlalchemy.orm import relationship

from ._base_ import Base


class LineData(Base):
    __tablename__ = 'LineData'
    Id = Column(Integer, primary_key=True, autoincrement=True, comment="主键")
    secondaryCoilId = Column(Integer, ForeignKey('SecondaryCoil.Id'), comment="关联的二级卷ID")
    surface = Column(String(2), comment="表面标识（S/L）")
    type = Column(String(20), comment="线类型")
    center_x = Column(Float, comment="中心X")
    center_y = Column(Float, comment="中心Y")
    width = Column(Float, comment="宽")
    height = Column(Float, comment="高")
    rotation_angle = Column(Float, comment="旋转角度")
    x1 = Column(Float, comment="起点X")
    y1 = Column(Float, comment="起点Y")
    x2 = Column(Float, comment="终点X")
    y2 = Column(Float, comment="终点Y")
    data = Column(Text, comment="检测数据")
    inner_min_value = Column(Float, comment="内侧最小值")
    inner_min_value_mm = Column(Float, comment="内侧最小值（毫米）")
    inner_max_value = Column(Float, comment="内侧最大值")
    inner_max_value_mm = Column(Float, comment="内侧最大值（毫米）")
    outer_min_value = Column(Float, comment="外侧最小值")
    outer_min_value_mm = Column(Float, comment="外侧最小值（毫米）")
    outer_max_value = Column(Float, comment="外侧最大值")
    outer_max_value_mm = Column(Float, comment="外侧最大值（毫米）")
    crateTime = Column(DateTime, server_default=func.now(), comment="创建时间")

    parent = relationship("SecondaryCoil", back_populates="childrenLineData")
