from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel

from app.models.customer import CustomerStatus, FollowUpType, Gender


class CustomerCreate(BaseModel):
    name: str
    phone: str
    gender: Optional[Gender] = Gender.unknown
    source_id: Optional[int] = None
    budget_range: Optional[str] = None
    wedding_date: Optional[date] = None
    note: Optional[str] = None
    assigned_sale_id: Optional[int] = None


class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    gender: Optional[Gender] = None
    source_id: Optional[int] = None
    status: Optional[CustomerStatus] = None
    budget_range: Optional[str] = None
    wedding_date: Optional[date] = None
    note: Optional[str] = None
    assigned_sale_id: Optional[int] = None
    version: int


class FollowUpCreate(BaseModel):
    type: FollowUpType
    content: str
    next_follow_at: Optional[datetime] = None


class TransferRequest(BaseModel):
    target_sale_id: int
