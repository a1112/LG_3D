from sqlalchemy import Column, Integer, ForeignKey, String, DateTime, func, Text
from sqlalchemy.orm import relationship

from ._base_ import Base


class CoilAlarmStatus(Base):
    """报警数据"""
    __tablename__ = 'CoilAlarmStatus'
    Id = Column(Integer, primary_key=True, autoincrement=True, comment="主键")
    secondaryCoilId = Column(Integer, ForeignKey('SecondaryCoil.Id'), comment="关联的二级卷ID")
    surface = Column(String(2), comment="表面标识（S/L）")
    level = Column(Integer, comment="报警等级")
    alarmStatus = Column(Integer, comment="报警状态码")
    alarmFlatRoll = Column(Integer, comment="扁卷报警标记")
    alarmTaper = Column(Integer, comment="塔形报警标记")
    alarmFolding = Column(Integer, comment="折叠报警标记")
    alarmDefect = Column(Integer, comment="缺陷报警标记")
    crateTime = Column(DateTime, server_default=func.now(), comment="创建时间")
    data = Column(Text(), comment="报警数据")
    parent = relationship("SecondaryCoil", back_populates="childrenCoilAlarmStatus")
