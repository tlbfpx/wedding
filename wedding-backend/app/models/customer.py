from __future__ import annotations
from typing import Optional
from sqlalchemy import String, Text, Enum as SAEnum, ForeignKey, Date
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin
from datetime import datetime
import enum


class CustomerStatus(str, enum.Enum):
    potential = "potential"
    following = "following"
    intention = "intention"
    signed = "signed"
    lost = "lost"


class Gender(str, enum.Enum):
    male = "male"
    female = "female"
    unknown = "unknown"


class Customer(Base, TimestampMixin):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    gender: Mapped[Gender] = mapped_column(SAEnum(Gender), default=Gender.unknown)
    source_id: Mapped[Optional[int]] = mapped_column(ForeignKey("customer_sources.id"), nullable=True)
    status: Mapped[CustomerStatus] = mapped_column(SAEnum(CustomerStatus), default=CustomerStatus.potential)
    budget_range: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    wedding_date: Mapped[Optional[datetime]] = mapped_column(Date, nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    assigned_sale_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    recycled_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)


class FollowUpType(str, enum.Enum):
    phone = "phone"
    wechat = "wechat"
    visit = "visit"
    other = "other"


class FollowUp(Base):
    __tablename__ = "follow_ups"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False)
    sale_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    type: Mapped[FollowUpType] = mapped_column(SAEnum(FollowUpType), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    next_follow_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)


class CustomerSource(Base):
    __tablename__ = "customer_sources"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
