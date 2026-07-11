from __future__ import annotations

"""create research radar tables

Revision ID: 20260711_0001
Revises:
Create Date: 2026-07-11 00:00:00
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260711_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "labs",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "sources",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("raw_metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "changes",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("new_facts", sa.JSON(), nullable=False),
        sa.Column("previous_state", sa.Text(), nullable=False),
        sa.Column("current_state", sa.Text(), nullable=False),
        sa.Column("change_summary", sa.Text(), nullable=False),
        sa.Column("importance", sa.String(length=1), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("next_watch_points", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "lab_profiles",
        sa.Column("lab_id", sa.String(length=64), sa.ForeignKey("labs.id"), primary_key=True),
        sa.Column("research_scope", sa.JSON(), nullable=False),
        sa.Column("watchlist", sa.JSON(), nullable=False),
        sa.Column("key_questions", sa.JSON(), nullable=False),
        sa.Column("update_frequency", sa.String(length=32), nullable=False),
    )
    op.create_table(
        "entity_states",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_name", sa.Text(), nullable=False),
        sa.Column("state_summary", sa.Text(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_id", sa.String(length=64), sa.ForeignKey("sources.id"), nullable=True),
        sa.Column("raw_metadata", sa.JSON(), nullable=False),
    )
    op.create_table(
        "lab_change_interpretations",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("lab_id", sa.String(length=64), sa.ForeignKey("labs.id"), nullable=False),
        sa.Column("change_id", sa.String(length=64), sa.ForeignKey("changes.id"), nullable=False),
        sa.Column("relevance_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("why_relevant", sa.Text(), nullable=False),
        sa.Column("impact", sa.Text(), nullable=False),
        sa.Column("next_watch_points", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("lab_id", "change_id", name="uq_lab_change_interpretation"),
    )


def downgrade() -> None:
    op.drop_table("lab_change_interpretations")
    op.drop_table("entity_states")
    op.drop_table("lab_profiles")
    op.drop_table("changes")
    op.drop_table("sources")
    op.drop_table("labs")
