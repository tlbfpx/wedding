"""
收支明细实体
"""
from __future__ import annotations
from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import DECIMAL, Date, ForeignKey, Integer, String, Text, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin

from app.finance.domain.entities.enums import TransactionType, ExpenseCategory


class Transaction(Base, TimestampMixin):
    """收支明细模型"""

    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    type: Mapped[TransactionType] = mapped_column(String(20), nullable=False)
    category: Mapped[Optional[ExpenseCategory]] = mapped_column(String(20), nullable=True)
    amount: Mapped[Decimal] = mapped_column(DECIMAL(12, 2), nullable=False)
    order_id: Mapped[Optional[int]] = mapped_column(ForeignKey("orders.id"), nullable=True)
    payment_id: Mapped[Optional[int]] = mapped_column(ForeignKey("finance_payments.id"), nullable=True)
    refund_id: Mapped[Optional[int]] = mapped_column(ForeignKey("refunds.id"), nullable=True)
    supplier_id: Mapped[Optional[int]] = mapped_column(ForeignKey("suppliers.id"), nullable=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    method: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_transactions_type", "type"),
        Index("ix_transactions_date", "date"),
        Index("ix_transactions_order_id", "order_id"),
        Index("ix_transactions_supplier_id", "supplier_id"),
        Index("ix_transactions_payment_id", "payment_id"),
        Index("ix_transactions_refund_id", "refund_id"),
    )
