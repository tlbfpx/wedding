"""
对账记录实体
"""
from __future__ import annotations
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Reconciliation(Base, TimestampMixin):
    """对账记录模型"""

    __tablename__ = "reconciliations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    period: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    snapshot: Mapped[str] = mapped_column(Text, nullable=False)  # JSON 格式的对账快照
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confirmed_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    confirmed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    __table_args__ = (
        Index("ix_reconciliations_period", "period"),
    )
