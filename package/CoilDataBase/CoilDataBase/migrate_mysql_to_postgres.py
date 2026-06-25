import argparse
import logging
import os
from typing import Dict, Iterable, List, Sequence

from sqlalchemy import URL, create_engine, func, select, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.exc import SQLAlchemyError

from .config import Config, DATABASE_URL_ENV, DeriverList
from .models import Base
from .storage_policy import skipped_table_names_for_log_and_raw

MYSQL_URL_ENV = "COIL_MYSQL_URL"

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s")
log = logging.getLogger(__name__)


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def default_mysql_url() -> str:
    url = URL.create(
        drivername=DeriverList.mysql.value,
        username=os.getenv("MYSQL_USER", Config.user),
        password=os.getenv("MYSQL_PASSWORD", Config.password),
        host=os.getenv("MYSQL_HOST", Config.host),
        port=_env_int("MYSQL_PORT", 3306),
        database=os.getenv("MYSQL_DATABASE", Config.database),
        query={"charset": os.getenv("MYSQL_CHARSET", Config.charset)},
    )
    return url.render_as_string(hide_password=False)


def _redact(url: str) -> str:
    return make_url(url).render_as_string(hide_password=True)


def _create_engine(url: str) -> Engine:
    return create_engine(url, pool_pre_ping=True)


def _table_count(connection, table) -> int:
    return int(
        connection.execute(select(
            func.count()).select_from(table)).scalar_one())


def _table_counts(connection, tables: Sequence | None = None) -> Dict[str, int]:
    counts = {}
    for table in tables or Base.metadata.sorted_tables:
        counts[table.name] = _table_count(connection, table)
    return counts


def _truncate_target(connection, tables: Sequence | None = None) -> None:
    dialect = connection.dialect
    preparer = dialect.identifier_preparer
    tables = list(tables or Base.metadata.sorted_tables)
    if not tables:
        return

    if dialect.name == "postgresql":
        table_sql = ", ".join(preparer.format_table(table) for table in tables)
        connection.execute(
            text(f"TRUNCATE TABLE {table_sql} RESTART IDENTITY CASCADE"))
        return

    for table in reversed(tables):
        connection.execute(table.delete())


def _batched(rows: Iterable[dict], batch_size: int) -> Iterable[List[dict]]:
    batch = []
    for row in rows:
        batch.append(row)
        if len(batch) >= batch_size:
            yield batch
            batch = []
    if batch:
        yield batch


def _source_batches(source_connection, table, batch_size: int) -> Iterable[List[dict]]:
    primary_keys = list(table.primary_key.columns)
    if len(primary_keys) == 1:
        primary_key = primary_keys[0]
        last_value = None
        while True:
            statement = select(table).order_by(primary_key).limit(batch_size)
            if last_value is not None:
                statement = statement.where(primary_key > last_value)
            rows = [
                dict(row._mapping)
                for row in source_connection.execute(statement).fetchall()
            ]
            if not rows:
                break
            last_value = rows[-1][primary_key.name]
            yield rows
        return

    result = source_connection.execution_options(stream_results=True).execute(
        select(table))
    rows = (dict(row._mapping) for row in result)
    yield from _batched(rows, batch_size)


def _clean_value(value):
    return value.replace("\x00", "") if isinstance(value, str) else value


def _clean_row(row: dict) -> dict:
    return {key: _clean_value(value) for key, value in row.items()}


def _copy_table_with_insert(source_connection, target_engine, table,
                            batch_size: int) -> int:
    total = 0
    for source_batch in _source_batches(source_connection, table, batch_size):
        batch = [_clean_row(row) for row in source_batch]
        with target_engine.begin() as target_connection:
            target_connection.execute(table.insert(), batch)
        total += len(batch)
        if total % 100000 == 0:
            log.info("copying %-24s %s rows...", table.name, total)
    return total


def _copy_table_with_postgres_copy(source_connection, target_engine, table,
                                   batch_size: int) -> int:
    total = 0
    columns = list(table.columns)
    preparer = target_engine.dialect.identifier_preparer
    table_sql = preparer.format_table(table)
    column_sql = ", ".join(preparer.format_column(column) for column in columns)
    copy_sql = f"COPY {table_sql} ({column_sql}) FROM STDIN"
    raw_connection = target_engine.raw_connection()
    try:
        for batch in _source_batches(source_connection, table, batch_size):
            try:
                with raw_connection.cursor() as cursor:
                    with cursor.copy(copy_sql) as copy:
                        for row in batch:
                            copy.write_row(
                                [_clean_value(row[column.name]) for column in columns])
                raw_connection.commit()
            except Exception:
                raw_connection.rollback()
                raise
            total += len(batch)
            if total % 100000 == 0:
                log.info("copying %-24s %s rows...", table.name, total)
    finally:
        raw_connection.close()
    return total


def _copy_table(source_connection, target_engine, table, batch_size: int) -> int:
    if target_engine.dialect.name == "postgresql":
        return _copy_table_with_postgres_copy(source_connection, target_engine,
                                             table, batch_size)
    return _copy_table_with_insert(source_connection, target_engine, table,
                                   batch_size)


def _selected_tables(skip_tables: set[str]) -> list:
    return [
        table for table in Base.metadata.sorted_tables
        if table.name not in skip_tables
    ]


def _reset_postgres_sequences(connection, tables: Sequence | None = None) -> None:
    if connection.dialect.name != "postgresql":
        return

    preparer = connection.dialect.identifier_preparer
    for table in tables or Base.metadata.sorted_tables:
        primary_keys = list(table.primary_key.columns)
        if len(primary_keys) != 1:
            continue
        column = primary_keys[0]
        table_name = preparer.format_table(table)
        sequence_name = connection.execute(
            text("SELECT pg_get_serial_sequence(:table_name, :column_name)"),
            {
                "table_name": table_name,
                "column_name": column.name
            },
        ).scalar()
        if not sequence_name:
            continue
        max_value = connection.execute(
            select(func.max(column)).select_from(table)).scalar()
        value = int(max_value or 1)
        is_called = bool(max_value)
        connection.execute(
            text(
                "SELECT setval(CAST(:sequence_name AS regclass), :value, :is_called)"
            ),
            {
                "sequence_name": sequence_name,
                "value": value,
                "is_called": is_called,
            },
        )


def migrate(source_url: str, target_url: str, batch_size: int, replace: bool,
            dry_run: bool, skip_tables: set[str] | None = None) -> None:
    source_backend = make_url(source_url).get_backend_name()
    target_backend = make_url(target_url).get_backend_name()
    if source_backend != "mysql":
        raise SystemExit(
            f"Source database must be MySQL, got {source_backend}: {_redact(source_url)}"
        )
    if target_backend != "postgresql":
        raise SystemExit(
            f"Target database must be PostgreSQL, got {target_backend}: {_redact(target_url)}"
        )

    log.info("source: %s", _redact(source_url))
    log.info("target: %s", _redact(target_url))
    skip_tables = set(skip_tables or set())
    tables = _selected_tables(skip_tables)
    if skip_tables:
        log.info("skipping tables: %s", sorted(skip_tables))

    source_engine = _create_engine(source_url)
    target_engine = _create_engine(target_url)

    source_connection = source_engine.connect()
    if source_backend == "mysql":
        source_connection = source_connection.execution_options(
            isolation_level="REPEATABLE READ")
        log.info("using MySQL REPEATABLE READ snapshot for source data")
    source_transaction = source_connection.begin()
    try:
        source_counts = _table_counts(source_connection, tables)
        log.info("source row counts: %s", source_counts)

        with target_engine.connect() as target_connection:
            target_counts = _table_counts(target_connection, tables)
        log.info("target row counts before migration: %s", target_counts)

        if dry_run:
            return

        if any(count > 0 for count in target_counts.values()) and not replace:
            raise SystemExit(
                "Target database is not empty. Use --replace to truncate and re-import."
            )

        if replace:
            with target_engine.begin() as target_connection:
                log.info("truncating target database...")
                _truncate_target(target_connection)

        copied_counts = {}
        try:
            for table in tables:
                copied = _copy_table(source_connection, target_engine, table,
                                     batch_size)
                copied_counts[table.name] = copied
                log.info("copied %-24s %s rows", table.name, copied)

            with target_engine.begin() as target_connection:
                _reset_postgres_sequences(target_connection, tables)
                final_counts = _table_counts(target_connection, tables)
        except SQLAlchemyError as exc:
            raise SystemExit(f"Migration failed: {exc}") from exc
    finally:
        source_transaction.rollback()
        source_connection.close()

    mismatches = {
        table_name:
        (source_counts[table_name], final_counts.get(table_name, 0))
        for table_name in source_counts
        if source_counts[table_name] != final_counts.get(table_name, 0)
    }
    if mismatches:
        raise SystemExit(f"Row count mismatch after migration: {mismatches}")

    log.info("migration complete. copied row counts: %s", copied_counts)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Migrate LG_3D CoilDataBase data from MySQL to PostgreSQL."
    )
    parser.add_argument("--source-url",
                        default=os.getenv(MYSQL_URL_ENV)
                        or default_mysql_url())
    parser.add_argument("--target-url", default=os.getenv(DATABASE_URL_ENV))
    parser.add_argument("--batch-size", type=int, default=1000)
    parser.add_argument("--replace",
                        action="store_true",
                        help="Truncate target tables before importing.")
    parser.add_argument("--dry-run",
                        action="store_true",
                        help="Only count source and target rows.")
    parser.add_argument("--skip-table",
                        action="append",
                        default=[],
                        help="Table name to skip. Can be specified multiple times.")
    parser.add_argument("--skip-log-and-raw",
                        action="store_true",
                        help="Skip log tables and raw LineData during migration.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.target_url:
        raise SystemExit(
            f"{DATABASE_URL_ENV} or --target-url is required for the PostgreSQL target."
        )
    skip_tables = set(args.skip_table or [])
    if args.skip_log_and_raw:
        skip_tables.update(skipped_table_names_for_log_and_raw())
    migrate(
        source_url=args.source_url,
        target_url=args.target_url,
        batch_size=max(args.batch_size, 1),
        replace=args.replace,
        dry_run=args.dry_run,
        skip_tables=skip_tables,
    )


if __name__ == "__main__":
    main()
