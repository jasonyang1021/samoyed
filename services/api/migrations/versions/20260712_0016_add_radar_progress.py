from __future__ import annotations

"""Add detailed progress fields to radar runs."""

from alembic import op
import sqlalchemy as sa


revision = "20260712_0016"
down_revision = "20260712_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("radar_runs", sa.Column("processed_sources", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("radar_runs", sa.Column("total_sources", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("radar_runs", sa.Column("current_source", sa.Text(), nullable=True))
    op.add_column("radar_runs", sa.Column("phase", sa.String(length=32), nullable=False, server_default="starting"))


def downgrade() -> None:
    op.drop_column("radar_runs", "phase")
    op.drop_column("radar_runs", "current_source")
    op.drop_column("radar_runs", "total_sources")
    op.drop_column("radar_runs", "processed_sources")
