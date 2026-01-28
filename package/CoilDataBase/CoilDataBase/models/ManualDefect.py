from sqlalchemy import Column, Integer, ForeignKey, String, DateTime, func, Text

from ._base_ import Base


class ManualDefect(Base):
    """
    手动标注缺陷数据表
    用于存储用户手动添加的缺陷标注
    """
    __tablename__ = 'ManualDefect'
    Id = Column(Integer, primary_key=True, autoincrement=True, comment="主键")
    secondaryCoilId = Column(Integer, ForeignKey('SecondaryCoil.Id'), comment="关联的二级卷ID")
    surface = Column(String(2), comment="表面标识（S/L）")
    defectClass = Column(Integer, comment="缺陷类型编号")
    defectName = Column(String(50), comment="缺陷名称")
    defectStatus = Column(Integer, default=1, comment="缺陷状态（0=忽略，1=正常）")
    defectX = Column(Integer, comment="缺陷X坐标")
    defectY = Column(Integer, comment="缺陷Y坐标")
    defectW = Column(Integer, comment="缺陷宽度")
    defectH = Column(Integer, comment="缺陷高度")
    defectSource = Column(Integer, default=0, comment="缺陷源值（手动标注默认0）")
    defectData = Column(Text(), comment="缺陷详细数据（JSON格式）")
    remark = Column(Text(), comment="备注信息")
    annotator = Column(String(50), comment="标注人")
    createTime = Column(DateTime, server_default=func.now(), comment="创建时间")
    updateTime = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")

    parent = relationship("SecondaryCoil", back_populates="childrenManualDefect")
