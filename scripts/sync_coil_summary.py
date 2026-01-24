#!/usr/bin/env python3
"""
同步 CoilSummary 摘要表脚本
用于修复列表数据滞后问题

用法:
    python scripts/sync_coil_summary.py       # 只同步缺失的记录
    python scripts/sync_coil_summary.py --all # 全量重新同步所有记录
    python scripts/sync_coil_summary.py --start 100 --end 200  # 指定范围同步
"""
import sys
import argparse
from pathlib import Path
from typing import Optional

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "package"))

from sqlalchemy import func
from CoilDataBase.CoilSummary import sync_coil_summary
from CoilDataBase.CoilSummary import SessionFactory
from CoilDataBase.models import CoilSummary, Coil, SecondaryCoil


def sync_missing_summaries(start_id: Optional[int] = None, end_id: Optional[int] = None, sync_all: bool = False):
    """同步缺失的摘要数据（一次性全部同步）

    Args:
        start_id: 起始ID
        end_id: 结束ID
        sync_all: 是否全量同步（忽略已有摘要，重新同步所有记录）
    """
    with SessionFactory() as session:
        # 获取最大ID - 使用 func.max 更安全地处理空表
        max_summary_id = session.query(func.max(CoilSummary.Id)).scalar() or 0
        max_coil_result = session.query(Coil.SecondaryCoilId).filter(
            Coil.SecondaryCoilId.isnot(None)
        ).order_by(Coil.SecondaryCoilId.desc()).first()

        max_coil_id = max_coil_result[0] if max_coil_result else None

        print(f"当前状态:")
        print(f"  CoilSummary 最大ID: {max_summary_id}")
        print(f"  Coil 最大ID: {max_coil_id}")

        if not max_coil_id:
            print("  ⚠ Coil 表为空，无需同步")
            return 0

        # 确定同步范围
        if sync_all:
            # 全量同步：从头开始
            sync_start = start_id if start_id else 1
            sync_end = end_id or max_coil_id
            print(f"  模式: 全量重新同步")
        else:
            # 增量同步：从最大摘要ID之后开始
            sync_start = max(max_summary_id + 1, start_id) if start_id else (max_summary_id + 1)
            sync_end = end_id or max_coil_id
            print(f"  模式: 增量同步")

        if sync_start > sync_end:
            print(f"  ✓ 摘要表已同步，无需操作")
            return 0

        print(f"  正在同步范围: {sync_start} -> {sync_end}")

        # 查询所有需要同步的coil IDs（一次性获取）
        coil_ids = [
            row[0] for row in session.query(Coil.SecondaryCoilId).filter(
                Coil.SecondaryCoilId.isnot(None),
                Coil.SecondaryCoilId >= sync_start,
                Coil.SecondaryCoilId <= sync_end
            ).distinct().all()
        ]

        if sync_all:
            # 全量同步：同步所有记录，包括已存在的
            sync_ids = coil_ids
            print(f"  需要同步 {len(sync_ids)} 条记录（全量）")
        else:
            # 增量同步：过滤掉已存在的摘要
            existing_ids = {row[0] for row in session.query(CoilSummary.Id).filter(
                CoilSummary.Id.in_(coil_ids)
            ).all()}
            sync_ids = [cid for cid in coil_ids if cid not in existing_ids]

            if not sync_ids:
                print(f"  ✓ 所有摘要已存在，无需同步")
                return 0

            print(f"  需要同步 {len(sync_ids)} 条记录")

        synced_count = 0
        for coil_id in sync_ids:
            try:
                sync_coil_summary(session, coil_id)
                synced_count += 1
                if synced_count % 10 == 0:
                    print(f"  已同步: {synced_count}/{len(sync_ids)}")
            except Exception as e:
                print(f"  ✗ 同步失败 {coil_id}: {e}")

        print(f"  ✓ 完成: 共同步 {synced_count} 条记录")

        # 验证同步结果
        new_max_summary_id = session.query(func.max(CoilSummary.Id)).scalar() or 0
        print(f"  当前 CoilSummary 最大ID: {new_max_summary_id}")

        return synced_count


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CoilSummary 摘要表同步工具")
    parser.add_argument("--all", action="store_true", help="全量重新同步所有记录")
    parser.add_argument("--start", type=int, help="起始ID")
    parser.add_argument("--end", type=int, help="结束ID")
    args = parser.parse_args()

    print("=" * 60)
    print("CoilSummary 摘要表同步工具")
    print("=" * 60)
    print()

    # 检查当前状态
    print("检查同步状态...")
    synced = sync_missing_summaries(start_id=args.start, end_id=args.end, sync_all=args.all)

    if synced > 0:
        print()
        print("✓ 同步成功！现在可以刷新前端列表查看最新数据。")
    else:
        print()
        print("✓ 摘要表已是最新状态。")

    print("=" * 60)
