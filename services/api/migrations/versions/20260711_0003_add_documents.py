from __future__ import annotations

"""add normalized documents for ingestion

Revision ID: 20260711_0003
Revises: 20260711_0002
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260711_0003"
down_revision: str | None = "20260711_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("source_id", sa.String(length=64), sa.ForeignKey("sources.id"), nullable=False),
        sa.Column("canonical_url", sa.Text(), nullable=False, unique=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("content_text", sa.Text(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("content_fingerprint", sa.String(length=64), nullable=False, unique=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("raw_metadata", sa.JSON(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("documents")
