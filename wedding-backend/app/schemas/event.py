import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.event import EventStatus, ResourceType


class EventCreate(BaseModel):
    order_id: Optional[int] = None
    title: str
    date: Optional[datetime.date] = None
    event_date: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    venue_id: Optional[int] = None
    planner_id: Optional[int] = None
    note: Optional[str] = None


class EventUpdate(BaseModel):
    title: Optional[str] = None
    date: Optional[datetime.date] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    venue_id: Optional[int] = None
    planner_id: Optional[int] = None
    status: Optional[EventStatus] = None
    note: Optional[str] = None


class ResourceInput(BaseModel):
    resource_type: ResourceType
    resource_id: int
    quantity: int = 1
    note: Optional[str] = None


class ConflictCheck(BaseModel):
    venue_id: Optional[int] = None
    date: datetime.date
    staff_ids: Optional[list[int]] = None
    exclude_event_id: Optional[int] = None
