from sqlalchemy import Column, Integer, ForeignKey, String, Text, DateTime, func
from sqlalchemy.orm import relationship

from ._base_ import Base


class AlarmFlatRollData(Base):
    __tablename__ = 'AlarmFlatRollData'
    Id = Column(Integer, primary_key=True, autoincrement=True, comment="主键")
    secondaryCoilId = Column(Integer, ForeignKey('SecondaryCoil.Id'), comment="关联的二级卷ID")
    surface = Column(String(2), comment="表面标识（S/L）")
    level = Column(Integer, comment="报警等级")
    err_msg = Column(Text, comment="报警信息")
    crateTime = Column(DateTime, server_default=func.now(), comment="创建时间")
    data = Column(Text, comment="检测结果数据")
    parent = relationship("SecondaryCoil", back_populates="childrenAlarmFlatRollData")
