from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from app.models.order import ApprovalType, ApprovalStatus


class ApprovalCreate(BaseModel):
    type: ApprovalType
    target_id: int
    reason: str


class ApprovalDecision(BaseModel):
    status: ApprovalStatus
    note: Optional[str] = None
