from __future__ import annotations

"""Add per-Lab source usage preferences."""

from alembic import op
import sqlalchemy as sa


revision = "20260712_0015"
down_revision = "20260712_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "lab_sources",
        sa.Column("lab_id", sa.String(length=64), sa.ForeignKey("labs.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("source_id", sa.String(length=64), sa.ForeignKey("sources.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("lab_sources")
