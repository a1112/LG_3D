from sqlalchemy import Column, Integer, ForeignKey, String, Float, Text, DateTime, func
from sqlalchemy.orm import relationship

from ._base_ import Base


class AlarmTaperShape(Base):
    """
    塔形检测
    """
    __tablename__ = 'AlarmTaperShape'
    Id = Column(Integer, primary_key=True, autoincrement=True, comment="主键")
    secondaryCoilId = Column(Integer, ForeignKey('SecondaryCoil.Id'), comment="关联的二级卷ID")
    surface = Column(String(2), comment="表面标识（S/L）")
    out_taper_max_x = Column(Integer, comment="外锥最大值X坐标")
    out_taper_max_y = Column(Integer, comment="外锥最大值Y坐标")
    out_taper_max_value = Column(Float, comment="外锥最大值")
    out_taper_min_x = Column(Integer, comment="外锥最小值X坐标")
    out_taper_min_y = Column(Integer, comment="外锥最小值Y坐标")
    out_taper_min_value = Column(Float, comment="外锥最小值")

    in_taper_max_x = Column(Integer, comment="内锥最大值X坐标")
    in_taper_max_y = Column(Integer, comment="内锥最大值Y坐标")
    in_taper_max_value = Column(Float, comment="内锥最大值")
    in_taper_min_x = Column(Integer, comment="内锥最小值X坐标")
    in_taper_min_y = Column(Integer, comment="内锥最小值Y坐标")
    in_taper_min_value = Column(Float, comment="内锥最小值")

    rotation_angle = Column(Float, comment="旋转角度")

    level = Column(Integer, comment="报警等级")
    err_msg = Column(Text, comment="报警信息")
    crateTime = Column(DateTime, server_default=func.now(), comment="创建时间")
    data = Column(Text(), comment="检测数据")

    parent = relationship("SecondaryCoil", back_populates="childrenAlarmTaperShape")
