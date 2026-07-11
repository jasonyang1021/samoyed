from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class AuthUserRead(BaseModel):
    authenticated: bool
    email: Optional[str] = None
    name: Optional[str] = None
    picture: Optional[str] = None
    role: str = "guest"
    oauth_configured: bool = False
    lab_ids: list[str] = []
    lab_names: list[str] = []


class LabMembershipRead(BaseModel):
    user_id: str
    lab_id: str
    lab_name: str
    email: str
    name: Optional[str] = None
    role: str


class LabMembershipUpdate(BaseModel):
    role: str


class LabInvitationCreate(BaseModel):
    email: str
    lab_id: str
    role: str


class LabInvitationRead(BaseModel):
    id: str
    email: str
    lab_id: str
    lab_name: str
    role: str
    status: str
    created_at: str
