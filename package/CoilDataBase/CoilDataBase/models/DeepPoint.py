from sqlalchemy import Column, Integer, ForeignKey, String, Float, Text, DateTime, func

from CoilDataBase.models._base_ import Base


class DeepPoint(Base):
    """
    深度点
    """
    __tablename__ = 'DeepPoint'
    Id = Column(Integer, primary_key=True, autoincrement=True)
    secondaryCoilId = Column(Integer, ForeignKey('SecondaryCoil.Id'))
    surface = Column(String(2))
    x = Column(Integer)
    y = Column(Integer)
    x_mm = Column(Float)
    y_mm = Column(Float)
    value = Column(Float)
    value_int = Column(Integer)
    by_user = Column(Integer)
    draw = Column(Integer)
    level = Column(Integer)
    err_msg = Column(Text)
    crateTime = Column(DateTime, server_default=func.now())
    data = Column(Text())
