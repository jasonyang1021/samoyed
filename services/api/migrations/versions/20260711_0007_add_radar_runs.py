from __future__ import annotations

"""add radar pipeline runs

Revision ID: 20260711_0007
Revises: 20260711_0006
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260711_0007"
down_revision: str | None = "20260711_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "radar_runs",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("source_count", sa.Integer(), nullable=False),
        sa.Column("documents_fetched", sa.Integer(), nullable=False),
        sa.Column("documents_created", sa.Integer(), nullable=False),
        sa.Column("analyzed", sa.Integer(), nullable=False),
        sa.Column("relevant", sa.Integer(), nullable=False),
        sa.Column("generated_changes", sa.Integer(), nullable=False),
        sa.Column("errors", sa.JSON(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("radar_runs")
