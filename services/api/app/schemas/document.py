from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class DocumentRead(BaseModel):
    id: str
    source_id: str
    canonical_url: str
    title: str
    content_text: str
    authors: list[str]
    content_level: str
    published_at: Optional[datetime]
    fetched_at: datetime
    status: str
    source_title: str
    source_type: str
    source_url: Optional[str]


class IngestResult(BaseModel):
    source_id: str
    source_title: str
    fetched: int
    created: int
    duplicates: int
    status: str
    error: Optional[str] = None


class WatchArticleRead(BaseModel):
    id: str
    title: str
    summary: str
    url: str
    image_url: Optional[str]
    published_at: Optional[datetime]
    source_title: str
    source_type: str


class SourceRead(BaseModel):
    id: str
    source_type: str
    title: str
    url: Optional[str]
    format: Optional[str]
    document_count: int
    latest_published_at: Optional[datetime]
    latest_fetched_at: Optional[datetime]
    status: str
    enabled: bool
    last_error: Optional[str]
    last_checked_at: Optional[datetime]


class LabSourceRead(BaseModel):
    lab_id: str
    source_id: str
    source_type: str
    title: str
    url: Optional[str]
    format: Optional[str]
    document_count: int
    status: str
    source_enabled: bool
    enabled: bool
    recommended: bool
    recommendation_reason: str
    last_error: Optional[str]


class LabSourceUpdate(BaseModel):
    enabled: bool


class LabSourceBatchUpdate(BaseModel):
    source_ids: list[str] = Field(default_factory=list, max_length=50)


class SourceRecommendationRead(BaseModel):
    lab_id: str
    lab_name: str
    source_id: str
    title: str
    source_type: str
    url: Optional[str]
    format: Optional[str]
    score: float
    reason: str
    enabled: bool
    source_enabled: bool
    requires_api_key: bool
