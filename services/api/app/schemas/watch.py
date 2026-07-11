from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class WatchItemRead(BaseModel):
    id: str
    kind: str
    name: str
    description: Optional[str]
    is_following: bool
    created_at: datetime


class WatchItemCreate(BaseModel):
    kind: str
    name: str
    description: Optional[str] = None

