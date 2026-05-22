from __future__ import annotations

from pydantic import BaseModel
from typing import Optional


class NotificationQuery(BaseModel):
    is_read: Optional[bool] = None
    type: Optional[str] = None
    page: int = 1
    page_size: int = 20


class NotificationReadRequest(BaseModel):
    ids: list[int]


class NotificationResponse(BaseModel):
    id: int
    title: str
    content: str
    type: str
    is_read: bool
    related_id: Optional[int] = None
    related_type: Optional[str] = None
    created_at: Optional[str] = None


class UnreadCountResponse(BaseModel):
    count: int
