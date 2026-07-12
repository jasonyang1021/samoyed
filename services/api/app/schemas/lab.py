from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class LabRead(BaseModel):
    id: str
    name: str
    description: Optional[str]
    admin_email: Optional[str] = None
    admin_name: Optional[str] = None


class LabCreate(BaseModel):
    name: str
    description: Optional[str] = None
    admin_email: Optional[str] = None


class LabUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    admin_email: Optional[str] = None


class LabProfileRead(BaseModel):
    lab_id: str
    research_scope: dict
    watchlist: dict
    key_questions: list
    signal_rules: dict
    ai_policy: dict
    update_frequency: str


class LabProfileUpdate(BaseModel):
    research_scope: dict = Field(default_factory=dict)
    watchlist: dict = Field(default_factory=dict)
    key_questions: list = Field(default_factory=list)
    signal_rules: dict = Field(default_factory=dict)
    ai_policy: dict = Field(default_factory=dict)
    update_frequency: str = "daily"


class LabWatchItemCreate(BaseModel):
    kind: str
    name: str
    description: Optional[str] = None


class LabWatchItemRead(BaseModel):
    id: str
    kind: str
    name: str
    description: Optional[str]
    is_following: bool
    created_at: datetime
