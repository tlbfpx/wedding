from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from app.models.user import TeamEnum, UserStatus


class UserCreate(BaseModel):
    username: str
    password: str
    name: str
    phone: Optional[str] = None
    role_id: int
    team: TeamEnum


class UserUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    role_id: Optional[int] = None
    team: Optional[TeamEnum] = None
    status: Optional[UserStatus] = None
    password: Optional[str] = None


class RoleUpdate(BaseModel):
    name: Optional[str] = None
    permissions: Optional[list[str]] = None
