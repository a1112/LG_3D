from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import database_exists, create_database

from .config import get_url
from .models import *


def ensure_runtime_indexes(engine_):
    """Create hot-path indexes for existing databases without requiring a manual migration."""
    inspector = inspect(engine_)
    try:
        existing_indexes = {item["name"] for item in inspector.get_indexes("CoilDefect")}
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
    engine_ = create_engine(url,
                            pool_size=5,
                            max_overflow=10,
                            pool_timeout=20,
                            pool_recycle=600,
                            pool_pre_ping=True,
                            echo=False
                            )
    if not database_exists(engine_.url):
        create_database(engine_.url)
    Base.metadata.create_all(engine_)
    ensure_runtime_indexes(engine_)
    return engine_, sessionmaker(bind=engine_)


engine, Session = get_engine()
