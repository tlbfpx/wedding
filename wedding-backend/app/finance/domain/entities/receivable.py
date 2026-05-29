"""
应收账款实体
"""
from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import DECIMAL, Date, ForeignKey, Integer, String, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin

from app.finance.domain.entities.enums import ReceivableStatus


class Receivable(Base, TimestampMixin):
    """应收账款模型"""

    __tablename__ = "receivables"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False, unique=True)
    total_amount: Mapped[Decimal] = mapped_column(DECIMAL(12, 2), nullable=False, default=Decimal("0"))
    received_amount: Mapped[Decimal] = mapped_column(DECIMAL(12, 2), nullable=False, default=Decimal("0"))
    status: Mapped[ReceivableStatus] = mapped_column(String(20), nullable=False, default=ReceivableStatus.unpaid)
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    overdue_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    __table_args__ = (
        Index("ix_receivables_order_id", "order_id"),
        Index("ix_receivables_status", "status"),
        Index("ix_receivables_due_date", "due_date"),
    )

    @property
    def remaining_amount(self) -> Decimal:
        """剩余应收金额"""
        return self.total_amount - self.received_amount

    @property
    def is_overdue(self) -> bool:
        """是否逾期"""
        if not self.due_date:
            return False
        return date.today() > self.due_date and self.received_amount < self.total_amount
