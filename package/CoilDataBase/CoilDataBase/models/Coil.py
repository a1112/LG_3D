from sqlalchemy import Column, Integer, ForeignKey, DateTime, func, Text
from sqlalchemy.orm import relationship

from ._base_ import Base


class Coil(Base):
    """
    检测数据
    """
    __tablename__ = 'Coil'
    Id = Column(Integer, primary_key=True, autoincrement=True, comment="主键")
    SecondaryCoilId = Column(Integer, ForeignKey('SecondaryCoil.Id'), comment="关联的二级卷ID")
    DetectionTime = Column(DateTime, server_default=func.now(), comment="检测时间")
    DefectCountS = Column(Integer, comment="小缺陷数量")
    DefectCountL = Column(Integer, comment="大缺陷数量")
    CheckStatus = Column(Integer, comment="检测状态")
    Status_L = Column(Integer, comment="长边状态")
    Status_S = Column(Integer, comment="短边状态")
    Grade = Column(Integer, comment="质量等级")
    Msg = Column(Text(), comment="备注信息")

    parent = relationship("SecondaryCoil", back_populates="childrenCoil")
