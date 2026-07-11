from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ScheduleRead(BaseModel):
    enabled: bool
    run_time: str
    timezone: str
    last_run_date: Optional[str]
    updated_at: datetime


class ScheduleUpdate(BaseModel):
    enabled: bool
    run_time: str
    timezone: str
