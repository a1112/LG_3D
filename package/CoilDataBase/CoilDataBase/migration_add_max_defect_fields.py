import logging
import sys
from pathlib import Path

from sqlalchemy import inspect, select, text
from sqlalchemy.schema import CreateColumn

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from CoilDataBase.CoilSummary import sync_coil_summary
from CoilDataBase.core import Session as SessionFactory
from CoilDataBase.models.CoilSummary import CoilSummary

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

MIGRATION_COLUMNS = (
    "MaxDefectName",
    "MaxDefectLevel",
    "MaxDefectSurface",
    "MaxDefectIsShown",
)


def _add_column_sql(engine, column):
    table_sql = engine.dialect.identifier_preparer.format_table(
        CoilSummary.__table__)
    column_sql = str(CreateColumn(column).compile(dialect=engine.dialect))
    return f"ALTER TABLE {table_sql} ADD COLUMN {column_sql}"


def add_columns_if_not_exist():
    with SessionFactory() as session:
        engine = session.get_bind()
        inspector = inspect(engine)
        existing_columns = {
            column["name"]
            for column in inspector.get_columns(CoilSummary.__tablename__)
        }
        missing_columns = [
            CoilSummary.__table__.c[name] for name in MIGRATION_COLUMNS
            if name not in existing_columns
        ]

        if not missing_columns:
            log.info(
                "MaxDefect columns already exist, skipping schema update.")
            return

        log.info("Adding %s columns to %s...", len(missing_columns),
                 CoilSummary.__tablename__)
        for column in missing_columns:
            session.execute(text(_add_column_sql(engine, column)))
        session.commit()
        log.info("MaxDefect columns added successfully.")


def recalculate_all_summaries():
    with SessionFactory() as session:
        result = session.execute(
            select(CoilSummary.Id).order_by(CoilSummary.Id.desc()))
        coil_ids = [row[0] for row in result.fetchall()]

        log.info("Found %s coil summaries to update.", len(coil_ids))

        for i, coil_id in enumerate(coil_ids):
            try:
                sync_coil_summary(session, coil_id)

                if (i + 1) % 100 == 0:
                    log.info("Processed %s/%s summaries.", i + 1,
                             len(coil_ids))
                    session.commit()
            except Exception as e:
                log.error("Error updating coil %s: %s", coil_id, e)
                session.rollback()

        session.commit()
        log.info("All summaries updated successfully.")


def main():
    log.info("=" * 60)
    log.info("Migration: Add MaxDefect fields to coil_summary")
    log.info("=" * 60)

    log.info("Step 1: Adding new columns...")
    add_columns_if_not_exist()

    log.info("Step 2: Recalculating defect data for all summaries...")
    recalculate_all_summaries()

    log.info("=" * 60)
    log.info("Migration completed successfully.")
    log.info("=" * 60)


if __name__ == "__main__":
    main()
