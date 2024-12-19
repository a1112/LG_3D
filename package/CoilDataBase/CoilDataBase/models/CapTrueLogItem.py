from sqlalchemy import Column, Integer, ForeignKey, String, DateTime, func

from CoilDataBase.models._base_ import Base


class CapTrueLogItem(Base):
    """
    记录采集日志
    """
    __tablename__ = 'CapTrueLogItem'
    Id = Column(Integer, primary_key=True, autoincrement=True)
    secondaryCoilId = Column(Integer, ForeignKey('SecondaryCoil.Id'))
    cameraId = Column(Integer)
    cameraName = Column(String(10))
    capTrueTime = Column(DateTime, server_default=func.now())
    imageIndex = Column(Integer)
