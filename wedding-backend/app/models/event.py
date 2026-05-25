from __future__ import annotations
from typing import Optional, List
from sqlalchemy import String, Text, Enum as SAEnum, ForeignKey, Date, Time, DECIMAL, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin
from datetime import datetime, date
import enum


class EventStatus(str, enum.Enum):
    draft = "draft"
    confirmed = "confirmed"
    executing = "executing"
    completed = "completed"
    cancelled = "cancelled"


class ResourceType(str, enum.Enum):
    staff = "staff"
    venue = "venue"
    vehicle = "vehicle"
    equipment = "equipment"
    other = "other"


class ScheduleStatus(str, enum.Enum):
    assigned = "assigned"
    confirmed = "confirmed"
    completed = "completed"


class Event(Base, TimestampMixin):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_id: Mapped[Optional[int]] = mapped_column(ForeignKey("orders.id"), unique=True, nullable=True)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    start_time: Mapped[Optional[datetime]] = mapped_column(Time, nullable=True)
    end_time: Mapped[Optional[datetime]] = mapped_column(Time, nullable=True)
    venue_id: Mapped[Optional[int]] = mapped_column(ForeignKey("venues.id"), nullable=True)
    status: Mapped[EventStatus] = mapped_column(SAEnum(EventStatus), default=EventStatus.draft)
    planner_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships for eager loading
    venue: Mapped[Optional["Venue"]] = relationship("Venue", lazy="joined")
    planner: Mapped[Optional["User"]] = relationship("User", foreign_keys=[planner_id], lazy="joined")
    resources: Mapped[List["EventResource"]] = relationship("EventResource", back_populates="event", lazy="selectin")
    staff_schedules: Mapped[List["StaffSchedule"]] = relationship("StaffSchedule", back_populates="event", lazy="selectin")

    __table_args__ = (
        Index("ix_events_date", "date"),
        Index("ix_events_status", "status"),
        Index("ix_events_planner_id", "planner_id"),
    )


class EventResource(Base):
    __tablename__ = "event_resources"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"), nullable=False)
    resource_type: Mapped[ResourceType] = mapped_column(SAEnum(ResourceType), nullable=False)
    resource_id: Mapped[int] = mapped_column(nullable=False)
    quantity: Mapped[int] = mapped_column(default=1)
    note: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Relationships
    event: Mapped["Event"] = relationship("Event", back_populates="resources")


class StaffSchedule(Base):
    __tablename__ = "staff_schedules"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    staff_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(30), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[ScheduleStatus] = mapped_column(SAEnum(ScheduleStatus), default=ScheduleStatus.assigned)

    # Relationships
    event: Mapped["Event"] = relationship("Event", back_populates="staff_schedules")

    __table_args__ = (
        Index("ix_staff_schedules_staff_id", "staff_id"),
        Index("ix_staff_schedules_date", "date"),
    )


class Venue(Base):
    __tablename__ = "venues"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    address: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    capacity: Mapped[Optional[int]] = mapped_column(nullable=True)
    contact: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    price: Mapped[Optional[float]] = mapped_column(DECIMAL(10, 2), nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
