from __future__ import annotations

"""add lab-specific watch items

Revision ID: 20260711_0011
Revises: 20260711_0010
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260711_0011"
down_revision: str | None = "20260711_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "lab_watch_items",
        sa.Column("lab_id", sa.String(length=64), sa.ForeignKey("labs.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("watch_item_id", sa.String(length=64), sa.ForeignKey("watch_items.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("lab_watch_items")
