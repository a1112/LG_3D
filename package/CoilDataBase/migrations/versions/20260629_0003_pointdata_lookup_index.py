"""add PointData lookup index.

Revision ID: 20260629_0003
Revises: 20260624_0002
Create Date: 2026-06-29
"""

from alembic import op


revision = "20260629_0003"
down_revision = "20260624_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "idx_pointdata_secondary_surface",
        "PointData",
        ["secondaryCoilId", "surface"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_pointdata_secondary_surface", table_name="PointData")
