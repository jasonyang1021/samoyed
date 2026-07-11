from __future__ import annotations

"""add lab invitations

Revision ID: 20260711_0010
Revises: 20260711_0009
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260711_0010"
down_revision: str | None = "20260711_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "lab_invitations",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("lab_id", sa.String(length=64), sa.ForeignKey("labs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("invited_by", sa.String(length=128), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_lab_invitations_email", "lab_invitations", ["email"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_lab_invitations_email", table_name="lab_invitations")
    op.drop_table("lab_invitations")
