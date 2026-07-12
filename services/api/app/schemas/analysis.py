from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class AnalysisRead(BaseModel):
    id: str
    document_id: str
    relevance_score: float
    is_relevant: bool
    category: str
    matched_entities: list[str]
    extracted_facts: list[str]
    summary: str
    confidence: Optional[float] = None
    evidence_citations: list[str] = Field(default_factory=list)
    provider: str = "rule_based"
    status: str
    analyzed_at: datetime
    generated_change_id: Optional[str] = None


class AnalysisRunResult(BaseModel):
    analyzed: int
    relevant: int
    generated_changes: int
    results: list[AnalysisRead]
