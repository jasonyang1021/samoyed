from __future__ import annotations

"""Track per-run AI/Dify analysis progress."""

from alembic import op
import sqlalchemy as sa


revision = "20260712_0017"
down_revision = "20260712_0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("radar_runs", sa.Column("analysis_total", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("radar_runs", sa.Column("dify_requests_total", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("radar_runs", sa.Column("dify_requests_succeeded", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("radar_runs", sa.Column("dify_requests_failed", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("radar_runs", "dify_requests_failed")
    op.drop_column("radar_runs", "dify_requests_succeeded")
    op.drop_column("radar_runs", "dify_requests_total")
    op.drop_column("radar_runs", "analysis_total")
