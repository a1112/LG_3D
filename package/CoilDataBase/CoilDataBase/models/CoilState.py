from ._base_ import *


class CoilState(Base):
    """状态数据"""
    __tablename__ = 'CoilState'
    Id = Column(Integer, primary_key=True, autoincrement=True, comment="主键")
    secondaryCoilId = Column(Integer, ForeignKey('SecondaryCoil.Id'), comment="关联的二级卷ID")
    surface = Column(String(2), comment="表面标识（S/L）")
    startTime = Column(DateTime, server_default=func.now(), comment="开始时间")
    scan3dCoordinateScaleX = Column(Float, comment="三维坐标缩放X")
    scan3dCoordinateScaleY = Column(Float, comment="三维坐标缩放Y")
    scan3dCoordinateScaleZ = Column(Float, comment="三维坐标缩放Z")
    rotate = Column(Integer, comment="旋转角度索引")
    x_rotate = Column(Integer, comment="X方向旋转角度索引")
    median_3d = Column(Float, comment="三维中位值")
    median_3d_mm = Column(Float, comment="三维中位值（毫米）")
    colorFromValue_mm = Column(Float, comment="颜色映射起始值（毫米）")
    colorToValue_mm = Column(Float, comment="颜色映射结束值（毫米）")
    start = Column(Float, comment="起始位置")
    step = Column(Float, comment="步长")
    upperLimit = Column(Float, comment="上限阈值")
    lowerLimit = Column(Float, comment="下限阈值")
    lowerArea = Column(Integer, comment="下限区域面积")
    upperArea = Column(Integer, comment="上限区域面积")
    lowerArea_percent = Column(Float, comment="下限区域面积占比")
    upperArea_percent = Column(Float, comment="上限区域面积占比")
    mask_area = Column(Integer, comment="遮罩面积")
    width = Column(Integer, comment="宽度像素")
    height = Column(Integer, comment="高度像素")
    jsonData = Column(Text(), comment="状态配置数据")

    parent = relationship("SecondaryCoil", back_populates="childrenCoilState")
