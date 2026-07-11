from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AnalysisRead(BaseModel):
    id: str
    document_id: str
    relevance_score: float
    is_relevant: bool
    category: str
    matched_entities: list[str]
    extracted_facts: list[str]
    summary: str
    status: str
    analyzed_at: datetime
    generated_change_id: Optional[str] = None


class AnalysisRunResult(BaseModel):
    analyzed: int
    relevant: int
    generated_changes: int
    results: list[AnalysisRead]
