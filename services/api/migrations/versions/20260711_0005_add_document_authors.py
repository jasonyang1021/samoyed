from __future__ import annotations

"""add document authors

Revision ID: 20260711_0005
Revises: 20260711_0004
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260711_0005"
down_revision: str | None = "20260711_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("authors", sa.JSON(), nullable=False, server_default="[]"))


def downgrade() -> None:
    op.drop_column("documents", "authors")
