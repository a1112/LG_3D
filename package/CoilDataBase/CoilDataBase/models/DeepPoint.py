from sqlalchemy import Column, Integer, ForeignKey, String, Float, Text, DateTime, func

from ._base_ import Base


class DeepPoint(Base):
    """
    深度点
    """
    __tablename__ = 'DeepPoint'
    Id = Column(Integer, primary_key=True, autoincrement=True, comment="主键")
    secondaryCoilId = Column(Integer, ForeignKey('SecondaryCoil.Id'), comment="关联的二级卷ID")
    surface = Column(String(2), comment="表面标识（S/L）")
    x = Column(Integer, comment="X像素坐标")
    y = Column(Integer, comment="Y像素坐标")
    x_mm = Column(Float, comment="X毫米坐标")
    y_mm = Column(Float, comment="Y毫米坐标")
    value = Column(Float, comment="深度值")
    value_int = Column(Integer, comment="深度值整数")
    by_user = Column(Integer, comment="用户标注标识")
    draw = Column(Integer, comment="是否用于绘制")
    level = Column(Integer, comment="报警等级")
    err_msg = Column(Text, comment="报警信息")
    crateTime = Column(DateTime, server_default=func.now(), comment="创建时间")
    data = Column(Text(), comment="原始/扩展数据")
