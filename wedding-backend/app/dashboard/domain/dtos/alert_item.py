"""Alert item DTO."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from app.dashboard.domain.value_objects import AlertLevel


@dataclass
class AlertItem:
    """Alert item."""
    id: str
    level: AlertLevel
    type: str
    title: str
    detail: str
    entity_type: str
    entity_id: int
    owner_id: Optional[int]
    owner_name: Optional[str]
    actions: list[str]
    created_at: datetime
