"""
财务收款记录实体
"""
from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import DECIMAL, DateTime, ForeignKey, Integer, String, Text, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin

from app.finance.domain.entities.enums import PaymentMethod


class FinancePayment(Base, TimestampMixin):
    """财务收款记录模型"""

    __tablename__ = "finance_payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(DECIMAL(12, 2), nullable=False)
    method: Mapped[PaymentMethod] = mapped_column(String(20), nullable=False)
    paid_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    __table_args__ = (
        Index("ix_finance_payments_order_id", "order_id"),
        Index("ix_finance_payments_paid_at", "paid_at"),
        Index("ix_finance_payments_created_by", "created_by"),
    )
