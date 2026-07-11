from __future__ import annotations

"""add users and lab memberships

Revision ID: 20260711_0009
Revises: 20260711_0008
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260711_0009"
down_revision: str | None = "20260711_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column("picture", sa.Text(), nullable=True),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=False)
    op.create_table(
        "lab_memberships",
        sa.Column("user_id", sa.String(length=128), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("lab_id", sa.String(length=64), sa.ForeignKey("labs.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("lab_memberships")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
