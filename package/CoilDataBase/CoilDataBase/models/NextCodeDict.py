from sqlalchemy import Column, Integer, String, Text

from ._base_ import Base


class NextCodeDict(Base):
    """
    下一工序
    """
    __tablename__ = 'NextCodeDict'
    Id = Column(Integer, primary_key=True, autoincrement=True, comment="主键")
    code = Column(String(2), comment="工序代码")
    info = Column(Text, comment="工序说明")
