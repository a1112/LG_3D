from sqlalchemy import Column, Integer, ForeignKey, String, DateTime, func

from ._base_ import Base


class CapTrueLog(Base):
    """
    记录采集日志
    """
    __tablename__ = 'CapTrueLog'
    Id = Column(Integer, primary_key=True, autoincrement=True, comment="主键")
    secondaryCoilId = Column(Integer, ForeignKey('SecondaryCoil.Id'), comment="关联的二级卷ID")
    cameraId = Column(Integer, comment="相机编号")
    cameraName = Column(String(10), comment="相机名称")
    capTrueStartTime = Column(DateTime, server_default=func.now(), comment="采集开始时间")
    capTrueEndTime = Column(DateTime, server_default=func.now(), comment="采集结束时间")
