from sqlalchemy import Column, Integer, ForeignKey, String, Text, DateTime, func
from sqlalchemy.orm import relationship

from CoilDataBase.models._base_ import Base


class AlarmInfo(Base):
    """
    报警表
    """
    __tablename__ = 'AlarmInfo'
    Id = Column(Integer, primary_key=True, autoincrement=True)
    secondaryCoilId = Column(Integer, ForeignKey('SecondaryCoil.Id'))
    surface = Column(String(2))
    nextCode = Column(String(2))
    nextName = Column(String(10))

    taperShapeGrad = Column(Integer)  # 塔形检测  报警等级
    taperShapeMsg = Column(Text)  # 塔形检测  报警信息

    looseCoilGrad = Column(Integer)  # 松卷检测  报警等级
    looseCoilMsg = Column(Text)  # 松卷检测  报警等级

    flatRollGrad = Column(Integer)  # 扁卷检测  报警等级
    flatRollMsg = Column(Text)  # 扁卷检测  报警等级

    defectGrad = Column(Integer)  # 缺陷检测  报警等级
    defectMsg = Column(Text)  # 缺陷检测  报警等级

    grad = Column(Integer)  # 综合  报警等级
    crateTime = Column(DateTime, server_default=func.now())
    data = Column(Text())  # 综合  报警数据

    parent = relationship("SecondaryCoil", back_populates="childrenAlarmInfo")
