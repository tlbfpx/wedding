from __future__ import annotations
from typing import Optional
from sqlalchemy import String, Text, Enum as SAEnum, ForeignKey, DECIMAL
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin
from datetime import datetime
import enum


class SupplierType(str, enum.Enum):
    four_gods = "four_gods"
    car = "car"
    venue = "venue"
    floral = "floral"
    photo = "photo"
    host = "host"
    other = "other"


class CooperationStatus(str, enum.Enum):
    active = "active"
    suspended = "suspended"
    blacklist = "blacklist"


class Supplier(Base, TimestampMixin):
    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[SupplierType] = mapped_column(SAEnum(SupplierType), nullable=False)
    contact: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    cooperation_status: Mapped[CooperationStatus] = mapped_column(
        SAEnum(CooperationStatus), default=CooperationStatus.active
    )
    rating: Mapped[float] = mapped_column(DECIMAL(2, 1), default=0.0)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class SupplierService(Base):
    __tablename__ = "supplier_services"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"), nullable=False)
    service_name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    price: Mapped[float] = mapped_column(DECIMAL(10, 2), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), default="次")
    note: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)


class SupplierEvaluation(Base):
    __tablename__ = "supplier_evaluations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"), nullable=False)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False)
    rating: Mapped[int] = mapped_column(nullable=False)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evaluator_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
