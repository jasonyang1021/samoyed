from __future__ import annotations

"""add rule analysis results

Revision ID: 20260711_0004
Revises: 20260711_0003
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260711_0004"
down_revision: str | None = "20260711_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "analyses",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("document_id", sa.String(length=64), sa.ForeignKey("documents.id"), nullable=False, unique=True),
        sa.Column("relevance_score", sa.Numeric(5, 2), nullable=False),
        sa.Column("is_relevant", sa.Boolean(), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("matched_entities", sa.JSON(), nullable=False),
        sa.Column("extracted_facts", sa.JSON(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("analyzed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("raw_result", sa.JSON(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("analyses")
