"""
卷材摘要表查询模块
实现懒加载缓存模式：优先从摘要表查询，如果没有则自动创建摘要
"""
import datetime
import logging
from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from .core import Session as SessionFactory
from .models import (
    SecondaryCoil, Coil, AlarmInfo, CoilSummary,
    CoilDefect, AlarmTaperShape, AlarmLooseCoil, AlarmFlatRoll
)

log = logging.getLogger(__name__)


def _decode_next_code(weight: float) -> str:
    """从 Weight 解码 NextCode"""
    try:
        if weight and isinstance(weight, (int, float)):
            return chr(int(weight))
    except (ValueError, TypeError):
        pass
    return ""


def sync_coil_summary(session: Session, coil_id: int) -> Optional[CoilSummary]:
    """
    同步单个卷材的摘要数据
    如果摘要不存在则创建，如果存在则更新

    处理多进程竞态条件：当多个进程同时创建同一摘要时，
    捕获重复键错误，重新查询后更新

    Args:
        session: 数据库会话
        coil_id: 卷材ID

    Returns:
        CoilSummary: 摘要对象
    """
    return _sync_coil_summary_impl(session, coil_id, retry_on_duplicate=True)


def _sync_coil_summary_impl(session: Session, coil_id: int, retry_on_duplicate: bool = False) -> Optional[CoilSummary]:
    """
    同步单个卷材的摘要数据（内部实现）

    Args:
        session: 数据库会话
        coil_id: 卷材ID
        retry_on_duplicate: 是否在重复键错误时重试
    """
    # 使用 no_autoflush 避免在查询时触发自动 flush
    with session.no_autoflush:
        # 先查找摘要是否已存在
        summary = session.query(CoilSummary).filter_by(Id=coil_id).first()
        is_new = summary is None

        if is_new:
            # 不存在，创建新实例
            summary = CoilSummary(Id=coil_id)

        # 获取原始数据
        coil = session.query(SecondaryCoil).filter_by(Id=coil_id).first()
        if not coil:
            log.warning(f"Coil {coil_id} not found for summary sync")
            return None

        # 只在创建新记录时添加到会话
        if is_new:
            session.add(summary)

        # 更新基本字段
        summary.CoilNo = coil.CoilNo
        summary.CreateTime = coil.CreateTime
        summary.CoilType = coil.CoilType
        summary.CoilInside = coil.CoilInside
        summary.CoilDia = coil.CoilDia
        summary.Thickness = coil.Thickness
        summary.Width = coil.Width
        summary.Weight = coil.Weight
        summary.ActWidth = coil.ActWidth

        # 解码 NextCode
        next_code = _decode_next_code(coil.Weight)
        summary.NextCode = next_code

        # 获取检测数据 (Coil) - 取最新的检测记录（按 DetectionTime 降序）
        check_data = session.query(Coil).filter_by(SecondaryCoilId=coil_id).order_by(Coil.DetectionTime.desc()).first()
        if check_data:
            summary.HasCoil = True
            summary.DefectCountS = check_data.DefectCountS or 0
            summary.DefectCountL = check_data.DefectCountL or 0
            summary.DetectionTime = check_data.DetectionTime
            summary.CheckStatus = check_data.CheckStatus or 0
            summary.Status_L = check_data.Status_L or 0
            summary.Status_S = check_data.Status_S or 0
            summary.Grade = check_data.Grade or 0
            # 从检测数据的 Weight 解码 NextCode
            if not next_code:
                summary.NextCode = _decode_next_code(check_data.DefectCountS)  # 原逻辑用Weight
        else:
            summary.HasCoil = False
            summary.DefectCountS = 0
            summary.DefectCountL = 0
            summary.CheckStatus = 0
            summary.Status_L = 0
            summary.Status_S = 0
            summary.Grade = 0

        # 获取 S 面报警
        alarm_s = session.query(AlarmInfo).filter_by(
            secondaryCoilId=coil_id, surface='S'
        ).first()

        if alarm_s:
            summary.S_HasAlarm = True
            summary.S_DefectGrad = alarm_s.defectGrad or 1
            summary.S_TaperShapeGrad = alarm_s.taperShapeGrad or 1
            summary.S_LooseCoilGrad = alarm_s.looseCoilGrad or 1
            summary.S_FlatRollGrad = alarm_s.flatRollGrad or 1
            summary.S_Grad = alarm_s.grad or max(
                summary.S_DefectGrad, summary.S_TaperShapeGrad,
                summary.S_LooseCoilGrad, summary.S_FlatRollGrad
            )
            summary.S_NextCode = alarm_s.nextCode or ""
            summary.S_NextName = alarm_s.nextName or ""
            # 覆盖 NextCode
            if alarm_s.nextCode:
                summary.NextCode = alarm_s.nextCode
                summary.NextInfo = alarm_s.nextName or ""
        else:
            summary.S_HasAlarm = False
            summary.S_DefectGrad = 1
            summary.S_TaperShapeGrad = 1
            summary.S_LooseCoilGrad = 1
            summary.S_FlatRollGrad = 1
            summary.S_Grad = 1

        # 获取 L 面报警
        alarm_l = session.query(AlarmInfo).filter_by(
            secondaryCoilId=coil_id, surface='L'
        ).first()

        if alarm_l:
            summary.L_HasAlarm = True
            summary.L_DefectGrad = alarm_l.defectGrad or 1
            summary.L_TaperShapeGrad = alarm_l.taperShapeGrad or 1
            summary.L_LooseCoilGrad = alarm_l.looseCoilGrad or 1
            summary.L_FlatRollGrad = alarm_l.flatRollGrad or 1
            summary.L_Grad = alarm_l.grad or max(
                summary.L_DefectGrad, summary.L_TaperShapeGrad,
                summary.L_LooseCoilGrad, summary.L_FlatRollGrad
            )
            summary.L_NextCode = alarm_l.nextCode or ""
            summary.L_NextName = alarm_l.nextName or ""
            # 覆盖 NextCode
            if alarm_l.nextCode and not summary.NextInfo:
                summary.NextCode = alarm_l.nextCode
                summary.NextInfo = alarm_l.nextName or ""
        else:
            summary.L_HasAlarm = False
            summary.L_DefectGrad = 1
            summary.L_TaperShapeGrad = 1
            summary.L_LooseCoilGrad = 1
            summary.L_FlatRollGrad = 1
            summary.L_Grad = 1

    # 在 no_autoflush 块外执行 flush/commit
    try:
        session.commit()
    except IntegrityError as e:
        # 多进程竞态条件：其他进程已经创建了这条记录
        if retry_on_duplicate and 'Duplicate entry' in str(e):
            session.rollback()
            log.debug(f"Duplicate entry detected for coil {coil_id}, re-querying and updating...")
            # 重新查询已存在的记录
            summary = session.query(CoilSummary).filter_by(Id=coil_id).first()
            if summary:
                # 重新填充数据（不设置 is_new，所以不会 add）
                return _sync_coil_summary_impl(session, coil_id, retry_on_duplicate=False)
            # 如果还是找不到，说明有其他问题
            log.warning(f"Coil {coil_id} still not found after duplicate error")
            return None
        else:
            # 其他类型的完整性错误，重新抛出
            raise

    log.info(f"Synced coil summary for {coil_id}: {summary.CoilNo}")
    return summary


def get_coil_list_with_summary(
    limit: int = 10,
    coil_id: Optional[int] = None,
    rev: bool = True,
    by_coil: bool = True,
    auto_sync: bool = True
) -> List[dict]:
    """
    获取卷材列表（优先使用摘要表）

    Args:
        limit: 返回数量
        coil_id: 起始ID（用于分页）
        rev: 是否倒序
        by_coil: 是否过滤已检测的卷材
        auto_sync: 是否自动同步缺失的摘要

    Returns:
        List[dict]: 格式化后的卷材列表
    """
    with SessionFactory() as session:
        # 基础查询
        query = session.query(CoilSummary)

        # 过滤条件
        if coil_id:
            if rev:
                # 向上刷新：获取更新的数据（Id > coil_id）
                query = query.filter(CoilSummary.Id > coil_id)
            else:
                query = query.filter(CoilSummary.Id < coil_id)

        # 如果只查询已检测的
        if by_coil:
            query = query.filter(CoilSummary.HasCoil == True)

        # 排序
        if rev:
            query = query.order_by(CoilSummary.Id.desc())
        else:
            query = query.order_by(CoilSummary.Id.asc())

        query = query.limit(limit)

        summaries = query.all()

        # 如果没有数据且启用自动同步，可能需要首次创建摘要
        if not summaries and auto_sync:
            log.info("No summaries found, attempting to sync from original data...")
            # 这里可以触发批量同步，但为避免长时间阻塞，先返回空
            # 由后台任务批量创建摘要

        # 转换为前端格式
        result = []
        for summary in summaries:
            result.append(summary.get_json())

        return result


def get_coil_list_original(
    limit: int = 10,
    coil_id: Optional[int] = None,
    rev: bool = True,
    by_coil: bool = True,
    sync_summary: bool = True
) -> List[dict]:
    """
    获取卷材列表（原始查询，带摘要同步）

    Args:
        limit: 返回数量
        coil_id: 起始ID
        rev: 是否倒序
        by_coil: 是否过滤已检测的卷材
        sync_summary: 是否同步创建摘要

    Returns:
        List[dict]: 格式化后的卷材列表
    """
    from sqlalchemy.orm import subqueryload

    with SessionFactory() as session:
        query = session.query(SecondaryCoil).options(
            subqueryload(SecondaryCoil.childrenAlarmInfo),
            subqueryload(SecondaryCoil.childrenCoil),
        )

        # 过滤条件
        if coil_id:
            if rev:
                # 向上刷新：获取更新的数据（Id > coil_id）
                query = query.filter(SecondaryCoil.Id > coil_id)
            else:
                query = query.filter(SecondaryCoil.Id < coil_id)

        if by_coil:
            last_coil = session.query(Coil).order_by(Coil.Id.desc()).first()
            if last_coil:
                query = query.filter(SecondaryCoil.Id <= last_coil.SecondaryCoilId)

        # 排序
        if rev:
            query = query.order_by(SecondaryCoil.Id.desc())
        else:
            query = query.order_by(SecondaryCoil.Id.asc())

        query = query.limit(limit)

        coils = query.all()

        # 格式化并可选同步摘要
        result = []
        for coil in coils:
            # 格式化数据
            coil_data = _format_coil_data(coil)

            # 同步创建摘要
            if sync_summary:
                try:
                    sync_coil_summary(session, coil.Id)
                except Exception as e:
                    log.error(f"Failed to sync summary for coil {coil.Id}: {e}")
                    # 回滚当前事务，确保后续操作可以继续
                    session.rollback()

            result.append(coil_data)

        return result


def _format_coil_data(coil: SecondaryCoil) -> dict:
    """格式化单个卷材数据（精简版，仅返回列表显示需要的字段）"""
    from . import tool
    from collections import defaultdict

    c_data = {
        "hasCoil": False,
        "hasAlarmInfo": False,
        "AlarmInfo": {},
        "defects": {},
        "childrenCoilDefect": [],
        "childrenCoilCheck": [],
    }

    # 获取检测数据
    if len(coil.childrenCoil) > 0:
        c_data["hasCoil"] = True
        for child_coil in coil.childrenCoil:
            coil_dict = tool.to_dict(child_coil)
            # 解码 NextCode
            if "Weight" in coil_dict and coil_dict["Weight"]:
                try:
                    code = chr(int(coil_dict["Weight"]))
                    coil_dict["NextCode"] = code
                except:
                    coil_dict["NextCode"] = ""
            c_data.update(coil_dict)

    # 获取报警数据
    if len(coil.childrenAlarmInfo) > 0:
        c_data["hasAlarmInfo"] = True
        for alarm in coil.childrenAlarmInfo:
            alarm_dict = tool.to_dict(alarm)
            # 添加 createTime 别名（QML 期望 createTime，数据库是 crateTime）
            if "crateTime" in alarm_dict:
                alarm_dict["createTime"] = alarm_dict["crateTime"]
            c_data["AlarmInfo"][alarm.surface] = alarm_dict
            # 更新 NextCode
            if alarm.nextCode:
                c_data["NextCode"] = alarm.nextCode
                c_data["NextInfo"] = alarm.nextName or ""

    # 获取缺陷数据（按 surface 分组）
    for defect in coil.childrenCoilDefect:
        defect_dict = tool.to_dict(defect)
        c_data["childrenCoilDefect"].append(defect_dict)

    # 获取检测校验数据
    for check in coil.childrenCoilCheck:
        check_dict = tool.to_dict(check)
        c_data["childrenCoilCheck"].append(check_dict)

    # 更新基本数据
    coil_dict = tool.to_dict(coil)
    c_data.update(coil_dict)

    return c_data


def batch_sync_summaries(limit: int = 1000) -> int:
    """
    批量同步摘要数据（用于初始化或后台任务）

    Args:
        limit: 最大同步数量

    Returns:
        int: 实际同步数量
    """
    with SessionFactory() as session:
        # 获取已检测的卷材ID
        detected_coils = session.query(
            Coil.SecondaryCoilId
        ).filter(
            Coil.SecondaryCoilId.isnot(None)
        ).distinct().limit(limit).all()

        synced_count = 0
        for (coil_id,) in detected_coils:
            try:
                # 检查是否已存在摘要
                existing = session.query(CoilSummary).filter_by(Id=coil_id).first()
                if not existing:
                    sync_coil_summary(session, coil_id)
                    synced_count += 1
            except Exception as e:
                log.error(f"Failed to sync summary for coil {coil_id}: {e}")
                # 回滚当前事务，确保后续操作可以继续
                session.rollback()

        log.info(f"Batch synced {synced_count} coil summaries")
        return synced_count


def get_coil_list_hybrid(
    limit: int = 10,
    coil_id: Optional[int] = None,
    rev: bool = True,
    by_coil: bool = True,
    auto_sync_latest: bool = True
) -> List[dict]:
    """
    混合模式：先查询 coil 表获取数据，然后同步到摘要表

    新逻辑：
    1. 先查询 Coil 表获取数据列表
    2. 对每个 coil，检查 coil_summary 是否存在
    3. 如果不存在，创建摘要
    4. 返回 coil_summary 的数据

    Args:
        limit: 返回数量
        coil_id: 起始ID
        rev: 是否倒序
        by_coil: 是否过滤已检测的卷材
        auto_sync_latest: 是否自动同步摘要（保留参数兼容性）

    Returns:
        List[dict]: 格式化后的卷材列表
    """
    from sqlalchemy.orm import subqueryload

    with SessionFactory() as session:
        # 构建 SecondaryCoil 查询
        query = session.query(SecondaryCoil.Id)

        # 过滤条件
        if coil_id:
            if rev:
                query = query.filter(SecondaryCoil.Id > coil_id)
            else:
                query = query.filter(SecondaryCoil.Id < coil_id)

        # 如果只查询已检测的卷材
        if by_coil:
            last_coil = session.query(Coil).order_by(Coil.Id.desc()).first()
            if last_coil:
                query = query.filter(SecondaryCoil.Id <= last_coil.SecondaryCoilId)

        # 排序
        if rev:
            query = query.order_by(SecondaryCoil.Id.desc())
        else:
            query = query.order_by(SecondaryCoil.Id.asc())

        query = query.limit(limit)

        # 获取 coil IDs
        coil_ids = [row[0] for row in query.all()]

        if not coil_ids:
            return []

        # 确保所有 coil 的摘要都存在
        for cid in coil_ids:
            try:
                # sync_coil_summary 内部会检查是否已存在，不存在才创建
                sync_coil_summary(session, cid)
            except Exception as e:
                log.error(f"Failed to sync summary for coil {cid}: {e}")
                session.rollback()

        # 从摘要表获取最终数据
        summaries = session.query(CoilSummary).filter(
            CoilSummary.Id.in_(coil_ids)
        ).order_by(CoilSummary.Id.desc() if rev else CoilSummary.Id.asc()).all()

        # 转换为前端格式
        result = []
        for summary in summaries:
            result.append(summary.get_json())

        return result


def get_coil_detail(coil_id: int) -> dict:
    """
    获取卷材详情（完整数据，包括缺陷、塔形等详细信息）

    Args:
        coil_id: 卷材ID

    Returns:
        dict: 完整的卷材详情数据
    """
    from sqlalchemy.orm import subqueryload
    from . import tool

    with SessionFactory() as session:
        query = session.query(SecondaryCoil).options(
            subqueryload(SecondaryCoil.childrenAlarmInfo),
            subqueryload(SecondaryCoil.childrenCoil),
            subqueryload(SecondaryCoil.childrenCoilDefect),
            subqueryload(SecondaryCoil.childrenCoilCheck),
            subqueryload(SecondaryCoil.childrenTaperShapePoint),
            subqueryload(SecondaryCoil.childrenAlarmTaperShape),
            subqueryload(SecondaryCoil.childrenAlarmLooseCoil),
            subqueryload(SecondaryCoil.childrenAlarmFlatRoll),
        )

        coil = query.filter_by(Id=coil_id).first()
        if not coil:
            return None

        # 格式化完整数据
        detail = _format_coil_detail(coil)
        return detail


def _format_coil_detail(coil: SecondaryCoil) -> dict:
    """格式化卷材详情数据（完全兼容原始查询格式）"""
    from . import tool

    c_data = {
        "hasCoil": False,
        "hasAlarmInfo": False,
        "AlarmInfo": {},
    }

    # 获取检测数据 (Coil)
    if len(coil.childrenCoil) > 0:
        c_data["hasCoil"] = True
        for child_coil in coil.childrenCoil:
            coil_dict = tool.to_dict(child_coil)
            # 解码 NextCode
            if "Weight" in coil_dict and coil_dict["Weight"]:
                try:
                    code = chr(int(coil_dict["Weight"]))
                    coil_dict["NextCode"] = code
                except:
                    coil_dict["NextCode"] = ""
            c_data.update(coil_dict)

    # 获取报警数据
    if len(coil.childrenAlarmInfo) > 0:
        c_data["hasAlarmInfo"] = True
        for alarm in coil.childrenAlarmInfo:
            alarm_dict = tool.to_dict(alarm)
            c_data["AlarmInfo"][alarm.surface] = alarm_dict
            # 更新 NextCode
            if alarm.nextCode:
                c_data["NextCode"] = alarm.nextCode
                c_data["NextInfo"] = alarm.nextName or ""

    # 缺陷数据
    c_data["childrenCoilDefect"] = []
    for defect in coil.childrenCoilDefect:
        c_data["childrenCoilDefect"].append(tool.to_dict(defect))

    # QML兼容：添加 defects 别名
    c_data["defects"] = c_data["childrenCoilDefect"]

    # 塔形点数据
    c_data["childrenTaperShapePoint"] = []
    for point in coil.childrenTaperShapePoint:
        c_data["childrenTaperShapePoint"].append(tool.to_dict(point))

    # 塔形报警数据
    c_data["childrenAlarmTaperShape"] = []
    for alarm in coil.childrenAlarmTaperShape:
        c_data["childrenAlarmTaperShape"].append(tool.to_dict(alarm))

    # 松卷报警数据
    c_data["childrenAlarmLooseCoil"] = []
    for alarm in coil.childrenAlarmLooseCoil:
        c_data["childrenAlarmLooseCoil"].append(tool.to_dict(alarm))

    # 扁卷报警数据
    c_data["childrenAlarmFlatRoll"] = []
    for alarm in coil.childrenAlarmFlatRoll:
        c_data["childrenAlarmFlatRoll"].append(tool.to_dict(alarm))

    # 检测校验数据
    c_data["childrenCoilCheck"] = []
    for check in coil.childrenCoilCheck:
        c_data["childrenCoilCheck"].append(tool.to_dict(check))

    # 更新基本数据
    coil_dict = tool.to_dict(coil)
    c_data.update(coil_dict)

    # 确保 SecondaryCoilId 存在
    if "SecondaryCoilId" not in c_data and "Id" in c_data:
        c_data["SecondaryCoilId"] = c_data["Id"]

    return c_data
