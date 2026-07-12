from __future__ import annotations

"""Add configurable Lab rules and AI evidence metadata."""

from alembic import op
import sqlalchemy as sa


revision = "20260712_0014"
down_revision = "20260712_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("lab_profiles", sa.Column("signal_rules", sa.JSON(), nullable=False, server_default="{}"))
    op.add_column("lab_profiles", sa.Column("ai_policy", sa.JSON(), nullable=False, server_default="{}"))
    op.add_column("analyses", sa.Column("confidence", sa.Numeric(5, 2), nullable=True))
    op.add_column("analyses", sa.Column("evidence_citations", sa.JSON(), nullable=False, server_default="[]"))
    op.add_column("analyses", sa.Column("provider", sa.String(length=32), nullable=False, server_default="rule_based"))


def downgrade() -> None:
    op.drop_column("analyses", "provider")
    op.drop_column("analyses", "evidence_citations")
    op.drop_column("analyses", "confidence")
    op.drop_column("lab_profiles", "ai_policy")
    op.drop_column("lab_profiles", "signal_rules")
