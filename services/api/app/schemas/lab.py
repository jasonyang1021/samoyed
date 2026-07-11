from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class LabRead(BaseModel):
    id: str
    name: str
    description: Optional[str]
