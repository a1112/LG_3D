"""strip raw fields from PointData.

Revision ID: 20260624_0002
Revises: 20260622_0001
Create Date: 2026-06-24
"""

from alembic import op


revision = "20260624_0002"
down_revision = "20260622_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute("""
CREATE OR REPLACE FUNCTION pointdata_strip_raw_fields()
RETURNS trigger AS $$
BEGIN
    NEW.x := NULL;
    NEW.y := NULL;
    NEW.z := NULL;
    NEW.data := NULL;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql
""")
    op.execute('DROP TRIGGER IF EXISTS trg_pointdata_strip_raw_fields ON "PointData"')
    op.execute("""
CREATE TRIGGER trg_pointdata_strip_raw_fields
BEFORE INSERT OR UPDATE ON "PointData"
FOR EACH ROW
EXECUTE FUNCTION pointdata_strip_raw_fields()
""")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute('DROP TRIGGER IF EXISTS trg_pointdata_strip_raw_fields ON "PointData"')
    op.execute("DROP FUNCTION IF EXISTS pointdata_strip_raw_fields()")
