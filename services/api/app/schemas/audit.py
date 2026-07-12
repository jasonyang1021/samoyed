from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class LabAuditLogRead(BaseModel):
    id: str
    lab_id: str
    actor_name: Optional[str]
    actor_email: Optional[str]
    action: str
    target: Optional[str]
    details: dict
    created_at: datetime
