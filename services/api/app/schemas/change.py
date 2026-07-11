from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class EvidenceRead(BaseModel):
    source_id: str
    source_title: str
    evidence_text: str
    url: Optional[str] = None


class ChangeCard(BaseModel):
    id: str
    title: str
    new_facts: list[str]
    change_summary: str
    previous_state: str
    current_state: str
    importance: str = Field(pattern="^(S|A|B|C)$")
    evidence: list[EvidenceRead]
    next_watch_points: list[str]
    affected_labs: list[str]
    watch_items: list[str]
    detected_at: datetime


class ChangeDetail(ChangeCard):
    status: str


class LabChangeCard(ChangeCard):
    why_relevant: str
    impact: str
    lab_next_watch_points: list[str]
