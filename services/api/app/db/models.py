from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, JSON, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Lab(Base):
    __tablename__ = "labs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    profile: Mapped["LabProfile"] = relationship(back_populates="lab", uselist=False)
    interpretations: Mapped[list["LabChangeInterpretation"]] = relationship(back_populates="lab")


class LabProfile(Base):
    __tablename__ = "lab_profiles"

    lab_id: Mapped[str] = mapped_column(String(64), ForeignKey("labs.id"), primary_key=True)
    research_scope: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    watchlist: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    key_questions: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    update_frequency: Mapped[str] = mapped_column(String(32), default="daily", nullable=False)

    lab: Mapped[Lab] = relationship(back_populates="profile")


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[Optional[str]] = mapped_column(Text)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    raw_metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class WatchItem(Base):
    __tablename__ = "watch_items"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    is_following: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class EntityState(Base):
    __tablename__ = "entity_states"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_name: Mapped[str] = mapped_column(Text, nullable=False)
    state_summary: Mapped[str] = mapped_column(Text, nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    source_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("sources.id"))
    raw_metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class Change(Base):
    __tablename__ = "changes"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    new_facts: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    previous_state: Mapped[str] = mapped_column(Text, nullable=False)
    current_state: Mapped[str] = mapped_column(Text, nullable=False)
    change_summary: Mapped[str] = mapped_column(Text, nullable=False)
    importance: Mapped[str] = mapped_column(String(1), nullable=False)
    evidence: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    next_watch_points: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    watch_item_ids: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="detected", nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    interpretations: Mapped[list["LabChangeInterpretation"]] = relationship(back_populates="change")


class LabChangeInterpretation(Base):
    __tablename__ = "lab_change_interpretations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    lab_id: Mapped[str] = mapped_column(String(64), ForeignKey("labs.id"), nullable=False)
    change_id: Mapped[str] = mapped_column(String(64), ForeignKey("changes.id"), nullable=False)
    relevance_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    why_relevant: Mapped[str] = mapped_column(Text, nullable=False)
    impact: Mapped[str] = mapped_column(Text, nullable=False)
    next_watch_points: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    lab: Mapped[Lab] = relationship(back_populates="interpretations")
    change: Mapped[Change] = relationship(back_populates="interpretations")
