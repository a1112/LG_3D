"""initial schema

Revision ID: 20260622_0001
Revises:
Create Date: 2026-06-22 00:00:00
"""
from alembic import op


revision = "20260622_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    from CoilDataBase.models import Base

    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    from CoilDataBase.models import Base

    Base.metadata.drop_all(bind=op.get_bind())
