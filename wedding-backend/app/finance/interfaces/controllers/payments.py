"""
收款登记 API
"""
from __future__ import annotations
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import require_permission
from app.finance.application.services import PaymentService
from app.finance.domain.entities.enums import PaymentMethod
from app.utils.pagination import PageResponse

router = APIRouter()


class PaymentCreate(BaseModel):
    """收款登记请求"""
    order_id: int
    amount: float
    method: PaymentMethod
    paid_at: Optional[datetime] = None
    note: Optional[str] = None


class PaymentUpdate(BaseModel):
    """收款修改请求"""
    amount: Optional[float] = None
    method: Optional[PaymentMethod] = None
    paid_at: Optional[datetime] = None
    note: Optional[str] = None


@router.post("")
async def create_payment(
    data: PaymentCreate,
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(require_permission("finance", "write")),
):
    """登记收款"""
    service = PaymentService(db)
    payment = await service.record_payment(
        order_id=data.order_id,
        amount=data.amount,
        method=data.method,
        paid_at=data.paid_at,
        note=data.note,
        created_by=ctx["user"].id,
    )

    return {
        "id": payment.id,
        "order_id": payment.order_id,
        "order_no": payment.order.order_no if hasattr(payment, 'order') and payment.order else None,
        "amount": str(payment.amount),
        "method": payment.method.value if isinstance(payment.method, PaymentMethod) else payment.method,
        "paid_at": payment.paid_at.isoformat() if payment.paid_at else None,
        "note": payment.note,
        "created_by": payment.created_by,
        "created_at": payment.created_at.isoformat() if payment.created_at else None,
    }


@router.get("")
async def list_payments(
    order_id: Optional[int] = Query(None),
    method: Optional[PaymentMethod] = Query(None),
    date_start: Optional[date] = Query(None),
    date_end: Optional[date] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(require_permission("finance", "read")),
):
    """收款记录列表"""
    service = PaymentService(db)
    items, total = await service.list_payments(
        order_id=order_id,
        method=method,
        date_start=date_start,
        date_end=date_end,
        page=page,
        page_size=page_size,
    )

    result_items = []
    for item in items:
        result_items.append({
            "id": item.id,
            "order_id": item.order_id,
            "order_no": item.order.order_no if hasattr(item, 'order') and item.order else None,
            "amount": str(item.amount),
            "method": item.method.value if isinstance(item.method, PaymentMethod) else item.method,
            "paid_at": item.paid_at.isoformat() if item.paid_at else None,
            "note": item.note,
            "created_by": item.created_by,
            "created_at": item.created_at.isoformat() if item.created_at else None,
        })

    return PageResponse(
        items=result_items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.put("/{payment_id}")
async def update_payment(
    payment_id: int,
    data: PaymentUpdate,
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(require_permission("finance", "write")),
):
    """修改收款记录"""
    service = PaymentService(db)
    payment = await service.update_payment(
        payment_id=payment_id,
        amount=data.amount,
        method=data.method,
        paid_at=data.paid_at,
        note=data.note,
    )

    return {
        "id": payment.id,
        "order_id": payment.order_id,
        "amount": str(payment.amount),
        "method": payment.method.value if isinstance(payment.method, PaymentMethod) else payment.method,
        "paid_at": payment.paid_at.isoformat() if payment.paid_at else None,
        "note": payment.note,
    }


@router.delete("/{payment_id}")
async def delete_payment(
    payment_id: int,
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(require_permission("finance", "write")),
):
    """删除收款记录"""
    service = PaymentService(db)
    await service.delete_payment(payment_id)
    return {"message": "收款记录已删除"}
