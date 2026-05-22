from __future__ import annotations
from enum import Enum as PyEnum
from typing import Optional
from sqlalchemy import String, Text, ForeignKey, Boolean, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin


class NotificationType(str, PyEnum):
    approval = "approval"
    schedule = "schedule"
    follow_up = "follow_up"
    system = "system"


class Notification(Base, TimestampMixin):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_user_unread", "user_id", "is_read"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text)
    type: Mapped[str] = mapped_column(String(20))
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    related_id: Mapped[Optional[int]] = mapped_column(default=None)
    related_type: Mapped[Optional[str]] = mapped_column(String(20), default=None)

    user = relationship("User", lazy="selectin")
