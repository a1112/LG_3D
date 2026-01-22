"""
卷材列表摘要表模型
用于快速查询列表显示的核心数据，避免复杂的JOIN操作
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, func, Boolean, Index
from ._base_ import Base


class CoilSummary(Base):
    """
    卷材列表摘要表
    冗余存储列表需要显示的核心数据，在数据写入/更新时同步更新
    如果摘要表没有数据，会自动查询原始数据并创建摘要
    """
    __tablename__ = 'coil_summary'

    # ========== 主键 ==========
    Id = Column(Integer, primary_key=True, comment="主键，关联 SecondaryCoil.Id")

    # ========== 基本信息 (来自 SecondaryCoil) ==========
    CoilNo = Column(String(50), comment="卷号")
    CreateTime = Column(DateTime, comment="创建时间")
    CoilType = Column(String(50), comment="卷类型")
    CoilInside = Column(Float, comment="内径")
    CoilDia = Column(Float, comment="卷径")
    Thickness = Column(Float, comment="厚度")
    Width = Column(Float, comment="宽度")
    Weight = Column(Float, comment="重量")
    ActWidth = Column(Float, comment="实际宽度")

    # 下一工序信息 (从 Coil.Weight 解码)
    NextCode = Column(String(10), comment="下一工序代码")
    NextInfo = Column(String(100), comment="下一工序名称")

    # ========== S面报警摘要 (来自 AlarmInfo WHERE surface='S') ==========
    S_DefectGrad = Column(Integer, default=1, comment="S面缺陷等级")
    S_TaperShapeGrad = Column(Integer, default=1, comment="S面塔形等级")
    S_LooseCoilGrad = Column(Integer, default=1, comment="S面松卷等级")
    S_FlatRollGrad = Column(Integer, default=1, comment="S面扁卷等级")
    S_Grad = Column(Integer, default=1, comment="S面综合等级 = MAX(上述4个)")
    S_HasAlarm = Column(Boolean, default=False, comment="S面是否有报警")
    S_NextCode = Column(String(10), comment="S面下一工序代码")
    S_NextName = Column(String(50), comment="S面下一工序名称")

    # ========== L面报警摘要 (来自 AlarmInfo WHERE surface='L') ==========
    L_DefectGrad = Column(Integer, default=1, comment="L面缺陷等级")
    L_TaperShapeGrad = Column(Integer, default=1, comment="L面塔形等级")
    L_LooseCoilGrad = Column(Integer, default=1, comment="L面松卷等级")
    L_FlatRollGrad = Column(Integer, default=1, comment="L面扁卷等级")
    L_Grad = Column(Integer, default=1, comment="L面综合等级 = MAX(上述4个)")
    L_HasAlarm = Column(Boolean, default=False, comment="L面是否有报警")
    L_NextCode = Column(String(10), comment="L面下一工序代码")
    L_NextName = Column(String(50), comment="L面下一工序名称")

    # ========== 检测摘要 (来自 Coil) ==========
    DefectCountS = Column(Integer, default=0, comment="S面缺陷数量")
    DefectCountL = Column(Integer, default=0, comment="L面缺陷数量")
    DetectionTime = Column(DateTime, comment="检测时间")
    CheckStatus = Column(Integer, default=0, comment="检测状态")
    Status_L = Column(Integer, default=0, comment="长边状态")
    Status_S = Column(Integer, default=0, comment="短边状态")
    Grade = Column(Integer, default=0, comment="质量等级")
    HasCoil = Column(Boolean, default=False, comment="是否有检测数据")

    # ========== 同步时间戳 ==========
    UpdateTime = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")

    # ========== 索引 ==========
    __table_args__ = (
        Index('idx_summary_id', 'Id'),
        Index('idx_summary_coilno', 'CoilNo'),
        Index('idx_summary_createtime', 'CreateTime'),
    )


    def get_json(self):
        """转换为字典格式，仅返回列表显示所需的字段

        QML 端实际使用的字段：
        - CoilModel: Id, CoilNo, CoilType, CoilInside, CoilDia, Thickness, Width,
                     Weight, ActWidth, CheckStatus, DefectCountS, DefectCountL,
                     Status_L, Grade, Status_S, Msg, NextInfo, NextCode,
                     CreateTime, DetectionTime, childrenCoilDefect, childrenCoilCheck
        - AlarmInfo: defectGrad, taperShapeGrad, looseCoilGrad, flatRollGrad, grad,
                     taperShapeMsg, looseCoilMsg, flatRollMsg, defectMsg,
                     nextCode, nextName, createTime (crateTime)
        """
        # S面报警数据（精简版，只返回列表需要的等级字段）
        alarm_s = {
            "secondaryCoilId": self.Id,
            "surface": "S",
            "defectGrad": self.S_DefectGrad,
            "taperShapeGrad": self.S_TaperShapeGrad,
            "looseCoilGrad": self.S_LooseCoilGrad,
            "flatRollGrad": self.S_FlatRollGrad,
            "grad": self.S_Grad,
            "nextCode": self.S_NextCode or "",
            "nextName": self.S_NextName or "",
            # QML 期望 createTime，对应数据库的 crateTime
            "createTime": self.UpdateTime,
            # Msg 字段不在摘要表中存储，需要详情时调用 detail API
            "taperShapeMsg": "",
            "looseCoilMsg": "",
            "flatRollMsg": "",
            "defectMsg": "",
        }

        # L面报警数据（精简版）
        alarm_l = {
            "secondaryCoilId": self.Id,
            "surface": "L",
            "defectGrad": self.L_DefectGrad,
            "taperShapeGrad": self.L_TaperShapeGrad,
            "looseCoilGrad": self.L_LooseCoilGrad,
            "flatRollGrad": self.L_FlatRollGrad,
            "grad": self.L_Grad,
            "nextCode": self.L_NextCode or "",
            "nextName": self.L_NextName or "",
            "createTime": self.UpdateTime,
            "taperShapeMsg": "",
            "looseCoilMsg": "",
            "flatRollMsg": "",
            "defectMsg": "",
        }

        return {
            "Id": self.Id,
            "CoilNo": self.CoilNo,
            "CreateTime": self.CreateTime,
            "CoilType": self.CoilType,
            "CoilInside": self.CoilInside,
            "CoilDia": self.CoilDia,
            "Thickness": self.Thickness,
            "Width": self.Width,
            "Weight": self.Weight,
            "ActWidth": self.ActWidth,
            "NextCode": self.NextCode or "",
            "NextInfo": self.NextInfo or "",
            "hasCoil": self.HasCoil,
            "hasAlarmInfo": self.S_HasAlarm or self.L_HasAlarm,
            "AlarmInfo": {
                "S": alarm_s,
                "L": alarm_l,
            },
            "DefectCountS": self.DefectCountS,
            "DefectCountL": self.DefectCountL,
            "DetectionTime": self.DetectionTime,
            "CheckStatus": self.CheckStatus,
            "Status_L": self.Status_L,
            "Status_S": self.Status_S,
            "Grade": self.Grade,
            "Msg": "",
            # 列表显示不需要缺陷和检查数据，需要时调用 detail API
            "defects": {},
            "childrenCoilDefect": [],
            "childrenCoilCheck": [],
        }

    def __repr__(self):
        return f"<CoilSummary(Id={self.Id}, CoilNo={self.CoilNo})>"
