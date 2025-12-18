from sqlalchemy import Column, Integer, String, Text

from ._base_ import Base


class DefectClassDict(Base):
    """
    缺陷类别数据
    """
    __tablename__ = 'DefectClassDict'
    Id = Column(Integer, primary_key=True, autoincrement=True, comment="主键")
    defectClass = Column(Integer, comment="缺陷类别编码")
    defectName = Column(String(10), comment="缺陷名称")
    defectType = Column(String(10), comment="缺陷类型")
    defectColor = Column(String(10), comment="显示颜色")
    defectLevel = Column(Integer, comment="缺陷等级")
    visible = Column(Integer, comment="是否可见")
    defectDesc = Column(Text(), comment="缺陷描述")
