from sqlalchemy import Column, Integer, String, Text

from CoilDataBase.models._base_ import Base


class NextCodeDict(Base):
    """
    下一工序
    """
    __tablename__ = 'NextCodeDict'
    Id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(2))
    info = Column(Text)
