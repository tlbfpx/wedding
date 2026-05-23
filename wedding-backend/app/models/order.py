from __future__ import annotations
from typing import Optional, List
from sqlalchemy import String, Text, Enum as SAEnum, ForeignKey, DECIMAL, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin
from datetime import datetime
import enum


class OrderStatus(str, enum.Enum):
    intention = "intention"
    signed = "signed"
    executing = "executing"
    completed = "completed"
    cancelled = "cancelled"


class ItemType(str, enum.Enum):
    planning = "planning"
    venue = "venue"
    floral = "floral"
    photo = "photo"
    host = "host"
    car = "car"
    other = "other"


class PaymentMethod(str, enum.Enum):
    cash = "cash"
    transfer = "transfer"
    wechat = "wechat"
    alipay = "alipay"
    card = "card"


class PaymentStatus(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"


class Order(Base, TimestampMixin):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_no: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False)
    planner_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    sale_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    status: Mapped[OrderStatus] = mapped_column(SAEnum(OrderStatus), default=OrderStatus.intention)
    total_amount: Mapped[float] = mapped_column(DECIMAL(12, 2), default=0)
    paid_amount: Mapped[float] = mapped_column(DECIMAL(12, 2), default=0)
    discount: Mapped[float] = mapped_column(DECIMAL(3, 2), default=1.00)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships for eager loading
    items: Mapped[List["OrderItem"]] = relationship("OrderItem", back_populates="order", lazy="selectin")
    payments: Mapped[List["Payment"]] = relationship("Payment", back_populates="order", lazy="selectin")
    contract: Mapped[Optional["Contract"]] = relationship("Contract", back_populates="order", uselist=False, lazy="joined")

    __table_args__ = (
        Index("ix_orders_status", "status"),
        Index("ix_orders_sale_id", "sale_id"),
        Index("ix_orders_planner_id", "planner_id"),
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False)
    type: Mapped[ItemType] = mapped_column(SAEnum(ItemType), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    quantity: Mapped[int] = mapped_column(default=1)
    unit_price: Mapped[float] = mapped_column(DECIMAL(10, 2), nullable=False)
    amount: Mapped[float] = mapped_column(DECIMAL(10, 2), nullable=False)
    supplier_id: Mapped[Optional[int]] = mapped_column(ForeignKey("suppliers.id"), nullable=True)
    note: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="items")


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False)
    amount: Mapped[float] = mapped_column(DECIMAL(12, 2), nullable=False)
    method: Mapped[PaymentMethod] = mapped_column(SAEnum(PaymentMethod), nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(SAEnum(PaymentStatus), default=PaymentStatus.pending)
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    note: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="payments")


class ContractStatus(str, enum.Enum):
    pending = "pending"
    signed = "signed"


class Contract(Base):
    __tablename__ = "contracts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False)
    file_url: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[ContractStatus] = mapped_column(SAEnum(ContractStatus), default=ContractStatus.pending)
    signed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="contract")


class ApprovalType(str, enum.Enum):
    discount = "discount"
    refund = "refund"
    cancel = "cancel"


class ApprovalStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class Approval(Base):
    __tablename__ = "approvals"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    type: Mapped[ApprovalType] = mapped_column(SAEnum(ApprovalType), nullable=False)
    target_id: Mapped[int] = mapped_column(nullable=False)
    applicant_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    approver_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    status: Mapped[ApprovalStatus] = mapped_column(SAEnum(ApprovalStatus), default=ApprovalStatus.pending)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    __table_args__ = (
        Index("ix_approvals_status", "status"),
    )
