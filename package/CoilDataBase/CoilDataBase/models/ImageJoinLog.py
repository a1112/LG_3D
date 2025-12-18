from sqlalchemy import Column, Integer, ForeignKey, String, DateTime, func, Float,Text
from sqlalchemy.orm import relationship

from ._base_ import Base


class ImageJoinLog(Base):
    """
    图像拼接，日志类

    """
    __tablename__ = "ImageJoinLog"
    Id = Column(Integer, primary_key=True, autoincrement=True, comment="主键")
    secondaryCoilId = Column(Integer, ForeignKey('SecondaryCoil.Id'), comment="关联的二级卷ID")
    surface = Column(String(2), comment="表面标识（S/L）")
    imageCount = Column(Integer, comment="图像数量")
    rotate = Column(Float, comment="旋转角度")
    flipH = Column(Integer, comment="水平翻转标志")
    flipV = Column(Integer, comment="垂直翻转标志")
    clip1L = Column(Integer, comment="裁剪1左")
    clip1R = Column(Integer, comment="裁剪1右")
    clip2L = Column(Integer, comment="裁剪2左")
    clip2R = Column(Integer, comment="裁剪2右")
    clip3L = Column(Integer, comment="裁剪3左")
    clip3R = Column(Integer, comment="裁剪3右")

    data = Column(Text, comment="拼接配置/结果数据")
    createTime = Column(DateTime, default=func.now(), comment="创建时间")
