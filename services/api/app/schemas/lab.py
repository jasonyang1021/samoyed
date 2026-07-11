from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class LabRead(BaseModel):
    id: str
    name: str
    description: Optional[str]


class LabCreate(BaseModel):
    name: str
    description: Optional[str] = None


class LabUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


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
