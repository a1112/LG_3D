from sqlalchemy import Column, Integer, ForeignKey, String, Text, DateTime, func
from sqlalchemy.orm import relationship

from ._base_ import Base


class AlarmInfo(Base):
    """
    报警信息
    """
    __tablename__ = 'AlarmInfo'
    Id = Column(Integer, primary_key=True, autoincrement=True, comment="主键")
    secondaryCoilId = Column(Integer, ForeignKey('SecondaryCoil.Id'), comment="关联的二级卷ID")
    surface = Column(String(2), comment="表面标识（S/L）")
    nextCode = Column(String(2), comment="下一工序代码")
    nextName = Column(String(10), comment="下一工序名称")

    taperShapeGrad = Column(Integer, comment="塔形检测报警等级")
    taperShapeMsg = Column(Text, comment="塔形检测报警信息")

    looseCoilGrad = Column(Integer, comment="松卷检测报警等级")
    looseCoilMsg = Column(Text, comment="松卷检测报警信息")

    flatRollGrad = Column(Integer, comment="扁卷检测报警等级")
    flatRollMsg = Column(Text, comment="扁卷检测报警信息")

    defectGrad = Column(Integer, comment="缺陷检测报警等级")
    defectMsg = Column(Text, comment="缺陷检测报警信息")

    grad = Column(Integer, comment="综合报警等级")
    crateTime = Column(DateTime, server_default=func.now(), comment="创建时间")
    data = Column(Text(), comment="综合报警数据")

    parent = relationship("SecondaryCoil", back_populates="childrenAlarmInfo")
