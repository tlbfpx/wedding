from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel

from app.models.order import ItemType, OrderStatus, PaymentMethod


class OrderItemInput(BaseModel):
    type: ItemType
    name: str
    quantity: int = 1
    unit_price: float
    supplier_id: Optional[int] = None
    note: Optional[str] = None


class OrderCreate(BaseModel):
    customer_id: int
    planner_id: Optional[int] = None
    sale_id: int
    discount: Optional[float] = 1.00
    note: Optional[str] = None
    items: list[OrderItemInput]


class OrderUpdate(BaseModel):
    note: Optional[str] = None
    discount: Optional[float] = None
    planner_id: Optional[int] = None


class StatusTransition(BaseModel):
    status: OrderStatus


class PaymentCreate(BaseModel):
    amount: float
    method: PaymentMethod
    note: Optional[str] = None
