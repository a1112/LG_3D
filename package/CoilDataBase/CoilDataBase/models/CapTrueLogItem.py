from sqlalchemy import Column, Integer, ForeignKey, String, DateTime, func

from ._base_ import Base


class CapTrueLogItem(Base):
    """
    记录采集日志
    """
    __tablename__ = 'CapTrueLogItem'
    Id = Column(Integer, primary_key=True, autoincrement=True, comment="主键")
    secondaryCoilId = Column(Integer, ForeignKey('SecondaryCoil.Id'), comment="关联的二级卷ID")
    cameraId = Column(Integer, comment="相机编号")
    cameraName = Column(String(10), comment="相机名称")
    capTrueTime = Column(DateTime, server_default=func.now(), comment="采集时间")
    imageIndex = Column(Integer, comment="图像索引")
