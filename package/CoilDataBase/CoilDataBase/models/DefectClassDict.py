from sqlalchemy import Column, Integer, String, Text

from ._base_ import Base


class DefectClassDict(Base):
    """
    缺陷类别数据
    """
    __tablename__ = 'DefectClassDict'
    Id = Column(Integer, primary_key=True, autoincrement=True)
    defectClass = Column(Integer)
    defectName = Column(String(10))
    defectType = Column(String(10))
    defectColor = Column(String(10))
    defectLevel = Column(Integer)
    visible = Column(Integer)
    defectDesc = Column(Text())
