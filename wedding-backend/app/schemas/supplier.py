from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from app.models.supplier import SupplierType, CooperationStatus


class SupplierCreate(BaseModel):
    name: str
    type: SupplierType
    contact: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    cooperation_status: Optional[CooperationStatus] = CooperationStatus.active
    note: Optional[str] = None


class SupplierUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[SupplierType] = None
    contact: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    cooperation_status: Optional[CooperationStatus] = None
    note: Optional[str] = None


class ServiceCreate(BaseModel):
    service_name: str
    description: Optional[str] = None
    price: float
    unit: Optional[str] = "次"
    note: Optional[str] = None


class ServiceUpdate(BaseModel):
    service_name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    unit: Optional[str] = None
    note: Optional[str] = None


class EvaluationCreate(BaseModel):
    order_id: int
    rating: int
    content: Optional[str] = None
