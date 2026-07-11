from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


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
