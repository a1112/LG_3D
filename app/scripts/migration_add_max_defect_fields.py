"""
数据库迁移脚本：为 coil_summary 表添加最严重缺陷字段

运行方式：
    cd D:\LCX_USER\LG_3D
    python app/scripts/migration_add_max_defect_fields.py

此脚本会：
1. 添加新字段到 coil_summary 表（如果不存在）
2. 重新计算所有现有记录的最严重缺陷数据
"""
import logging
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "package" / "CoilDataBase"))

from sqlalchemy import create_engine, text
from CoilDataBase.core import Session as SessionFactory
from CoilDataBase.CoilSummary import sync_coil_summary

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)


def add_columns_if_not_exist(engine):
    """添加新列到 coil_summary 表（如果不存在）"""
    with engine.connect() as conn:
        # 检查列是否存在
        result = conn.execute(text(
            "SHOW COLUMNS FROM coil_summary LIKE 'MaxDefectName'"
        ))
        max_defect_name_exists = result.fetchone() is not None

        if not max_defect_name_exists:
            log.info("Adding new columns to coil_summary table...")
            conn.execute(text(
                "ALTER TABLE coil_summary "
                "ADD COLUMN MaxDefectName VARCHAR(50) DEFAULT '' COMMENT '最严重缺陷名称', "
                "ADD COLUMN MaxDefectLevel INT DEFAULT 0 COMMENT '最严重缺陷等级（0表示无缺陷）', "
                "ADD COLUMN MaxDefectSurface VARCHAR(2) DEFAULT '' COMMENT '最严重缺陷所在表面（S/L）', "
                "ADD COLUMN MaxDefectIsShown BOOLEAN DEFAULT TRUE COMMENT '最严重缺陷是否显示（未被屏蔽）'"
            ))
            conn.commit()
            log.info("New columns added successfully!")
        else:
            log.info("Columns already exist, skipping...")


def recalculate_all_summaries():
    """重新计算所有现有 coil_summary 记录的最严重缺陷数据"""
    with SessionFactory() as session:
        # 获取所有摘要记录的 ID
        result = session.execute(text("SELECT Id FROM coil_summary ORDER BY Id DESC"))
        coil_ids = [row[0] for row in result.fetchall()]

        log.info(f"Found {len(coil_ids)} coil summaries to update...")

        for i, coil_id in enumerate(coil_ids):
            try:
                # 调用同步函数重新计算摘要（包含新的缺陷字段）
                sync_coil_summary(session, coil_id)

                if (i + 1) % 100 == 0:
                    log.info(f"Processed {i + 1}/{len(coil_ids)} summaries...")
                    session.commit()  # 每100条提交一次
            except Exception as e:
                log.error(f"Error updating coil {coil_id}: {e}")
                session.rollback()

        session.commit()
        log.info("All summaries updated successfully!")


def main():
    """主函数"""
    log.info("=" * 60)
    log.info("Migration: Add MaxDefect fields to coil_summary")
    log.info("=" * 60)

    # 创建引擎用于检查列
    from CoilDataBase.core import engine

    # Step 1: 添加新列
    log.info("Step 1: Adding new columns...")
    add_columns_if_not_exist(engine)

    # Step 2: 重新计算所有摘要数据
    log.info("\nStep 2: Recalculating defect data for all summaries...")
    recalculate_all_summaries()

    log.info("\n" + "=" * 60)
    log.info("Migration completed successfully!")
    log.info("=" * 60)


if __name__ == "__main__":
    main()
