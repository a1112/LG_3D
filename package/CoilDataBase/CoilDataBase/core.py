from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import database_exists, create_database

from .config import get_url
from .db_settings import sqlalchemy_pool_settings
from .models import *


def ensure_runtime_indexes(engine_):
    """Create hot-path indexes for existing databases without requiring a manual migration."""
    inspector = inspect(engine_)
    try:
        existing_indexes = {
            item["name"]
            for item in inspector.get_indexes("CoilDefect")
        }
    except Exception:
        existing_indexes = set()

    statements = []
    if "idx_coil_defect_secondary_coil_id" not in existing_indexes:
        statements.append(
            "CREATE INDEX idx_coil_defect_secondary_coil_id ON CoilDefect (secondaryCoilId)"
        )
    if "idx_coil_defect_secondary_surface" not in existing_indexes:
        statements.append(
            "CREATE INDEX idx_coil_defect_secondary_surface ON CoilDefect (secondaryCoilId, surface)"
        )

    try:
        existing_manual_indexes = {
            item["name"]
            for item in inspector.get_indexes("ManualDefect")
        }
    except Exception:
        existing_manual_indexes = set()

    if "idx_manual_defect_secondary_coil_id" not in existing_manual_indexes:
        statements.append(
            "CREATE INDEX idx_manual_defect_secondary_coil_id ON ManualDefect (secondaryCoilId)"
        )
    if "idx_manual_defect_secondary_surface" not in existing_manual_indexes:
        statements.append(
            "CREATE INDEX idx_manual_defect_secondary_surface ON ManualDefect (secondaryCoilId, surface)"
        )

    if not statements:
        return

    with engine_.begin() as connection:
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
    if not database_exists(engine_.url):
        create_database(engine_.url)
    Base.metadata.create_all(engine_)
    ensure_runtime_indexes(engine_)
    return engine_, sessionmaker(bind=engine_)


engine, Session = get_engine()
