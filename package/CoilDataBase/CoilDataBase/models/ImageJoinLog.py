from sqlalchemy import Column, Integer, ForeignKey, String, DateTime, func, Float,Text
from sqlalchemy.orm import relationship

from ._base_ import Base


class ImageJoinLog(Base):
    """
    图像拼接，日志类

    """
    __tablename__ = "ImageJoinLog"
    Id = Column(Integer, primary_key=True, autoincrement=True)
    secondaryCoilId = Column(Integer, ForeignKey('SecondaryCoil.Id'))
    surface = Column(String(2))
    imageCount = Column(Integer)
    rotate = Column(Float)
    flipH = Column(Integer)
    flipV = Column(Integer)
    clip1L = Column(Integer)
    clip1R = Column(Integer)
    clip2L = Column(Integer)
    clip2R = Column(Integer)
    clip3L = Column(Integer)
    clip3R = Column(Integer)

    data = Column(Text)
    createTime = Column(DateTime, default=func.now())
