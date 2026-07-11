from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class RadarRunRead(BaseModel):
    id: str
    started_at: datetime
    finished_at: Optional[datetime]
    status: str
    source_count: int
    documents_fetched: int
    documents_created: int
    analyzed: int
    relevant: int
    generated_changes: int
    errors: list[str]
