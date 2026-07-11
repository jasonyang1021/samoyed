from __future__ import annotations

"""add document content level

Revision ID: 20260711_0006
Revises: 20260711_0005
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260711_0006"
down_revision: str | None = "20260711_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("content_level", sa.String(length=32), nullable=False, server_default="metadata"))


def downgrade() -> None:
    op.drop_column("documents", "content_level")
