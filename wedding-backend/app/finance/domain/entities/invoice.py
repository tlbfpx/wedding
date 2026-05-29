"""
开票记录实体
"""
from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import DECIMAL, DateTime, ForeignKey, Integer, String, Text, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin

from app.finance.domain.entities.enums import InvoiceType, InvoiceStatus


class Invoice(Base, TimestampMixin):
    """开票记录模型"""

    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False)
    invoice_type: Mapped[InvoiceType] = mapped_column(String(20), nullable=False)
    amount: Mapped[Decimal] = mapped_column(DECIMAL(12, 2), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    tax_no: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[InvoiceStatus] = mapped_column(String(20), nullable=False, default=InvoiceStatus.pending)
    invoice_no: Mapped[Optional[str]] = mapped_column(String(50), unique=True, nullable=True)
    pdf_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    issued_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    voided_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    voided_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    approval_id: Mapped[Optional[int]] = mapped_column(ForeignKey("approvals.id"), nullable=True)

    __table_args__ = (
        Index("ix_invoices_order_id", "order_id"),
        Index("ix_invoices_status", "status"),
        Index("ix_invoices_invoice_no", "invoice_no"),
    )
