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
    memberships: Mapped[list["LabMembership"]] = relationship(back_populates="lab")
    watch_items: Mapped[list["LabWatchItem"]] = relationship(back_populates="lab", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True, index=True)
    name: Mapped[Optional[str]] = mapped_column(Text)
    picture: Mapped[Optional[str]] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(32), default="guest", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    memberships: Mapped[list["LabMembership"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class LabMembership(Base):
    __tablename__ = "lab_memberships"

    user_id: Mapped[str] = mapped_column(String(128), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    lab_id: Mapped[str] = mapped_column(String(64), ForeignKey("labs.id", ondelete="CASCADE"), primary_key=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    user: Mapped[User] = relationship(back_populates="memberships")
    lab: Mapped[Lab] = relationship(back_populates="memberships")


class LabInvitation(Base):
    __tablename__ = "lab_invitations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    lab_id: Mapped[str] = mapped_column(String(64), ForeignKey("labs.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    invited_by: Mapped[Optional[str]] = mapped_column(String(128), ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    lab: Mapped[Lab] = relationship()
    inviter: Mapped[Optional[User]] = relationship(foreign_keys=[invited_by])


class LabWatchItem(Base):
    __tablename__ = "lab_watch_items"

    lab_id: Mapped[str] = mapped_column(String(64), ForeignKey("labs.id", ondelete="CASCADE"), primary_key=True)
    watch_item_id: Mapped[str] = mapped_column(String(64), ForeignKey("watch_items.id", ondelete="CASCADE"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    lab: Mapped[Lab] = relationship(back_populates="watch_items")
    watch_item: Mapped["WatchItem"] = relationship()


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

    documents: Mapped[list["Document"]] = relationship(back_populates="source")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_id: Mapped[str] = mapped_column(String(64), ForeignKey("sources.id"), nullable=False)
    canonical_url: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    content_text: Mapped[str] = mapped_column(Text, nullable=False)
    authors: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    content_level: Mapped[str] = mapped_column(String(32), default="metadata", nullable=False)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    content_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(32), default="new", nullable=False)
    raw_metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    source: Mapped[Source] = relationship(back_populates="documents")
    analysis: Mapped[Optional["Analysis"]] = relationship(back_populates="document", uselist=False)


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    document_id: Mapped[str] = mapped_column(String(64), ForeignKey("documents.id"), nullable=False, unique=True)
    relevance_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    is_relevant: Mapped[bool] = mapped_column(nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    matched_entities: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    extracted_facts: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="completed", nullable=False)
    analyzed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    raw_result: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    document: Mapped[Document] = relationship(back_populates="analysis")


class RadarRun(Base):
    __tablename__ = "radar_runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32), default="running", nullable=False)
    source_count: Mapped[int] = mapped_column(default=0, nullable=False)
    documents_fetched: Mapped[int] = mapped_column(default=0, nullable=False)
    documents_created: Mapped[int] = mapped_column(default=0, nullable=False)
    analyzed: Mapped[int] = mapped_column(default=0, nullable=False)
    relevant: Mapped[int] = mapped_column(default=0, nullable=False)
    generated_changes: Mapped[int] = mapped_column(default=0, nullable=False)
    errors: Mapped[list] = mapped_column(JSON, default=list, nullable=False)


class RadarSettings(Base):
    __tablename__ = "radar_settings"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    enabled: Mapped[bool] = mapped_column(default=False, nullable=False)
    run_time: Mapped[str] = mapped_column(String(5), default="08:00", nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Tokyo", nullable=False)
    last_run_date: Mapped[Optional[str]] = mapped_column(String(10))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class WatchItem(Base):
    __tablename__ = "watch_items"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    is_following: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    lab_links: Mapped[list[LabWatchItem]] = relationship(back_populates="watch_item", cascade="all, delete-orphan")


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
    generation_method: Mapped[str] = mapped_column(String(32), default="rule_based", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    lab: Mapped[Lab] = relationship(back_populates="interpretations")
    change: Mapped[Change] = relationship(back_populates="interpretations")
