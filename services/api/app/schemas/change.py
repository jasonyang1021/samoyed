from datetime import datetime
from pydantic import BaseModel, Field


class ChangeCard(BaseModel):
    id: str
    title: str
    change_summary: str
    previous_state: str
    current_state: str
    importance: str = Field(pattern="^(S|A|B|C)$")
    affected_labs: list[str]
    evidence_count: int
    published_at: datetime
