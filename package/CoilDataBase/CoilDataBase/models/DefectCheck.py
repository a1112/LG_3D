from sqlalchemy import Column, Integer, ForeignKey, String, DateTime, func, Float, Text
from sqlalchemy.orm import relationship

from ._base_ import Base


class DefectCheck(Base):
    __tablename__ = 'DefectCheck'
    Id = Column(Integer, primary_key=True, autoincrement=True, comment="主键")

    secondaryCoilId = Column(Integer, ForeignKey('SecondaryCoil.Id'), comment="关联的二级卷ID")
    defectId = Column(Integer, ForeignKey('CoilDefect.Id'), comment="关联的缺陷ID")
    key = Column(String(5), comment="检验键值")
    status = Column(Integer, comment="检验状态")
    oldDefectId = Column(Integer, comment="原缺陷ID")
    oldDefectName = Column(String(10), comment="原缺陷名称")
    newDefectId = Column(Integer, comment="新缺陷ID")
    newDefectName = Column(String(10), comment="新缺陷名称")
    addTime = Column(DateTime, comment="添加时间")
    msg = Column(Text, comment="备注信息")


    parent = relationship("SecondaryCoil", back_populates="childrenDefectCheck")
    parent_defect = relationship("CoilDefect", back_populates="children_defect_check")
