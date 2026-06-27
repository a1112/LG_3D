import os

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import database_exists, create_database

from .config import get_url
from .db_settings import sqlalchemy_pool_settings
from .models import *


def _env_flag(name: str) -> bool:
    value = os.getenv(name, "")
    return value.lower() in {"1", "true", "yes", "on"}


def is_postgresql_url(url: str) -> bool:
    return make_url(url).get_backend_name() == "postgresql"


def should_auto_create_schema(url: str) -> bool:
    if not is_postgresql_url(url):
        return True
    return _env_flag("COIL_DATABASE_AUTO_CREATE")


def ensure_runtime_indexes(engine_):
    """Create hot-path indexes for existing databases without requiring a manual migration."""
    inspector = inspect(engine_)
    is_postgresql = engine_.dialect.name == "postgresql"
    table_names = set(inspector.get_table_names())

    statements = []

    def existing_index_names(table_name: str) -> set[str]:
        try:
            return {item["name"] for item in inspector.get_indexes(table_name)}
        except Exception:
            return set()

    def add_index(table_name: str, index_name: str, columns_sql: str) -> None:
        if table_name not in table_names:
            return
        if index_name in existing_index_names(table_name):
            return
        if is_postgresql:
            statements.append(f'CREATE INDEX CONCURRENTLY IF NOT EXISTS {index_name} ON "{table_name}" ({columns_sql})')
        else:
            statements.append(f"CREATE INDEX {index_name} ON {table_name} ({columns_sql})")

    if is_postgresql:
        add_index("CoilDefect", "idx_coil_defect_secondary_coil_id", '"secondaryCoilId"')
        add_index("CoilDefect", "idx_coil_defect_secondary_surface", '"secondaryCoilId", surface')
        add_index("ManualDefect", "idx_manual_defect_secondary_coil_id", '"secondaryCoilId"')
        add_index("ManualDefect", "idx_manual_defect_secondary_surface", '"secondaryCoilId", surface')
        add_index("Coil", "idx_coil_secondary_coil_id", '"SecondaryCoilId"')
        add_index("CoilState", "idx_coil_state_secondary_coil_id", '"secondaryCoilId"')
        add_index("CoilState", "idx_coil_state_secondary_surface_id", '"secondaryCoilId", surface, "Id" DESC')
        add_index("AlarmInfo", "idx_alarm_info_secondary_surface", '"secondaryCoilId", surface')
        add_index("AlarmFlatRoll", "idx_alarm_flat_roll_secondary", '"secondaryCoilId"')
        add_index("AlarmTaperShape", "idx_alarm_taper_shape_secondary", '"secondaryCoilId"')
        add_index("AlarmLooseCoil", "idx_alarm_loose_coil_secondary", '"secondaryCoilId"')
        add_index("coil_summary", "idx_summary_hascoil_id_desc", '"HasCoil", "Id" DESC')
    else:
        add_index("CoilDefect", "idx_coil_defect_secondary_coil_id", "secondaryCoilId")
        add_index("CoilDefect", "idx_coil_defect_secondary_surface", "secondaryCoilId, surface")
        add_index("ManualDefect", "idx_manual_defect_secondary_coil_id", "secondaryCoilId")
        add_index("ManualDefect", "idx_manual_defect_secondary_surface", "secondaryCoilId, surface")
        add_index("Coil", "idx_coil_secondary_coil_id", "SecondaryCoilId")
        add_index("CoilState", "idx_coil_state_secondary_coil_id", "secondaryCoilId")
        add_index("CoilState", "idx_coil_state_secondary_surface_id", "secondaryCoilId, surface, Id DESC")
        add_index("AlarmInfo", "idx_alarm_info_secondary_surface", "secondaryCoilId, surface")
        add_index("AlarmFlatRoll", "idx_alarm_flat_roll_secondary", "secondaryCoilId")
        add_index("AlarmTaperShape", "idx_alarm_taper_shape_secondary", "secondaryCoilId")
        add_index("AlarmLooseCoil", "idx_alarm_loose_coil_secondary", "secondaryCoilId")
        add_index("coil_summary", "idx_summary_hascoil_id_desc", "HasCoil, Id DESC")

    if not statements:
        return

    connection_context = (
        engine_.connect().execution_options(isolation_level="AUTOCOMMIT")
        if is_postgresql else engine_.begin()
    )
    with connection_context as connection:
        for statement in statements:
            try:
                connection.execute(text(statement))
            except OperationalError as exc:
                # MySQL duplicate index error: create_all may have already created it.
                if "Duplicate key name" not in str(exc):
                    raise


def get_engine(url=None):
    if url is None:
        url = get_url()
    engine_ = create_engine(url, **sqlalchemy_pool_settings())
    auto_create_schema = should_auto_create_schema(url)
    if auto_create_schema and not database_exists(engine_.url):
        create_database(engine_.url)
    if auto_create_schema:
        Base.metadata.create_all(engine_)
        ensure_runtime_indexes(engine_)
    return engine_, sessionmaker(bind=engine_)


engine, Session = get_engine()
