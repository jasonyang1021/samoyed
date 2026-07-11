from __future__ import annotations

"""add radar scheduler settings

Revision ID: 20260711_0008
Revises: 20260711_0007
"""
from collections.abc import Sequence
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa


revision: str = "20260711_0008"
down_revision: str | None = "20260711_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "radar_settings",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("run_time", sa.String(length=5), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("last_run_date", sa.String(length=10), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    settings = sa.table(
        "radar_settings",
        sa.column("id", sa.String),
        sa.column("enabled", sa.Boolean),
        sa.column("run_time", sa.String),
        sa.column("timezone", sa.String),
        sa.column("updated_at", sa.DateTime),
    )
    op.bulk_insert(settings, [{"id": "default", "enabled": False, "run_time": "08:00", "timezone": "Asia/Tokyo", "updated_at": datetime.now(timezone.utc)}])


def downgrade() -> None:
    op.drop_table("radar_settings")
