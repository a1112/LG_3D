from sqlalchemy import Column, Integer, ForeignKey, String, Float, Text, DateTime, func
from sqlalchemy.orm import relationship

from ._base_ import Base


class AlarmFlatRoll(Base):
    """
    扁卷检测，弃用，下版本中移除该数据结构
    """
    __tablename__ = 'AlarmFlatRoll'
    Id = Column(Integer, primary_key=True, autoincrement=True, comment="主键")
    secondaryCoilId = Column(Integer, ForeignKey('SecondaryCoil.Id'), comment="关联的二级卷ID")
    surface = Column(String(2), comment="表面标识（S/L）")
    out_circle_width = Column(Float, comment="外圆宽度")
    out_circle_height = Column(Float, comment="外圆高度")
    out_circle_center_x = Column(Float, comment="外圆中心X")
    out_circle_center_y = Column(Float, comment="外圆中心Y")
    out_circle_radius = Column(Float, comment="外圆半径")
    inner_circle_width = Column(Float, comment="内圆宽度")
    inner_circle_height = Column(Float, comment="内圆高度")
    inner_circle_center_x = Column(Float, comment="内圆中心X")
    inner_circle_center_y = Column(Float, comment="内圆中心Y")
    inner_circle_radius = Column(Float, comment="内圆半径")
    accuracy_x = Column(Float, comment="X方向精度")
    accuracy_y = Column(Float, comment="Y方向精度")
    level = Column(Integer, comment="报警等级")
    err_msg = Column(Text, comment="报警信息")
    crateTime = Column(DateTime, server_default=func.now(), comment="创建时间")
    data = Column(Text(), comment="检测结果数据")

    parent = relationship("SecondaryCoil", back_populates="childrenAlarmFlatRoll")
