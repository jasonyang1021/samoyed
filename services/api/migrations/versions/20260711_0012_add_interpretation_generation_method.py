"""add interpretation generation method

Revision ID: 20260711_0012
Revises: 20260711_0011
"""

from alembic import op
import sqlalchemy as sa

revision = "20260711_0012"
down_revision = "20260711_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("lab_change_interpretations", sa.Column("generation_method", sa.String(length=32), nullable=False, server_default="rule_based"))


def downgrade() -> None:
    op.drop_column("lab_change_interpretations", "generation_method")
