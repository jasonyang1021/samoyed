"""add source health fields and lab audit logs

Revision ID: 20260712_0013
Revises: 20260711_0012
"""

from alembic import op
import sqlalchemy as sa

revision = "20260712_0013"
down_revision = "20260711_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sources", sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("sources", sa.Column("last_error", sa.Text(), nullable=True))
    op.add_column("sources", sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True))
    op.create_table(
        "lab_audit_logs",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("lab_id", sa.String(length=64), sa.ForeignKey("labs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("actor_user_id", sa.String(length=128), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("target", sa.Text(), nullable=True),
        sa.Column("details", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("lab_audit_logs")
    op.drop_column("sources", "last_checked_at")
    op.drop_column("sources", "last_error")
    op.drop_column("sources", "enabled")
