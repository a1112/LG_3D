from sqlalchemy import Column, Integer, ForeignKey, String, DateTime, func, Float, Text
from sqlalchemy.orm import relationship

from ._base_ import Base


class CoilDefect(Base):
    """
    缺陷数据
    """
    __tablename__ = 'CoilDefect'
    Id = Column(Integer, primary_key=True, autoincrement=True, comment="主键")
    secondaryCoilId = Column(Integer, ForeignKey('SecondaryCoil.Id'), comment="关联的二级卷ID")
    surface = Column(String(2), comment="表面标识（S/L）")
    defectClass = Column(Integer, comment="缺陷类型编号")
    defectName = Column(String(10), comment="缺陷名称")
    defectStatus = Column(Integer, comment="缺陷状态")
    defectTime = Column(DateTime, server_default=func.now(), comment="缺陷出现时间")
    defectX = Column(Integer, comment="缺陷X坐标")
    defectY = Column(Integer, comment="缺陷Y坐标")
    defectW = Column(Integer, comment="缺陷宽度")
    defectH = Column(Integer, comment="缺陷高度")
    defectSource = Column(Float, comment="缺陷源值")
    defectData = Column(Text(), comment="缺陷详细数据")

    parent = relationship("SecondaryCoil", back_populates="childrenCoilDefect")
    children_defect_check = relationship("DefectCheck", back_populates="parent_defect")
