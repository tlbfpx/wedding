"""
收支明细 API
"""
from __future__ import annotations
from datetime import date
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import require_permission
from app.finance.application.services import TransactionService
from app.finance.domain.entities.enums import TransactionType, ExpenseCategory
from app.utils.pagination import PageResponse

router = APIRouter()


class ExpenseCreate(BaseModel):
    """支出登记请求"""
    category: ExpenseCategory
    amount: float
    order_id: Optional[int] = None
    supplier_id: Optional[int] = None
    date: Optional[date] = None
    note: Optional[str] = None


class ExpenseUpdate(BaseModel):
    """支出修改请求"""
    amount: Optional[float] = None
    category: Optional[ExpenseCategory] = None
    note: Optional[str] = None


@router.get("")
async def list_transactions(
    type: Optional[TransactionType] = Query(None),
    category: Optional[ExpenseCategory] = Query(None),
    order_id: Optional[int] = Query(None),
    supplier_id: Optional[int] = Query(None),
    date_start: Optional[date] = Query(None),
    date_end: Optional[date] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(require_permission("finance", "read")),
):
    """收支明细列表"""
    service = TransactionService(db)
    items, total = await service.list_transactions(
        type=type,
        category=category,
        order_id=order_id,
        supplier_id=supplier_id,
        date_start=date_start,
        date_end=date_end,
        page=page,
        page_size=page_size,
    )

    result_items = []
    for item in items:
        result_items.append({
            "id": item.id,
            "type": item.type.value if isinstance(item.type, TransactionType) else item.type,
            "category": item.category.value if item.category and isinstance(item.category, ExpenseCategory) else item.category,
            "amount": str(item.amount),
            "order_id": item.order_id,
            "order_no": item.order.order_no if hasattr(item, 'order') and item.order and hasattr(item.order, 'order_no') else None,
            "supplier_id": item.supplier_id,
            "supplier_name": item.supplier.name if hasattr(item, 'supplier') and item.supplier else None,
            "date": item.date.isoformat() if item.date else None,
            "method": item.method,
            "note": item.note,
            "created_at": item.created_at.isoformat() if item.created_at else None,
        })

    return PageResponse(
        items=result_items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.post("")
async def create_expense(
    data: ExpenseCreate,
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(require_permission("finance", "write")),
):
    """手动登记支出"""
    service = TransactionService(db)
    transaction = await service.create_expense_transaction(
        category=data.category,
        amount=data.amount,
        order_id=data.order_id,
        supplier_id=data.supplier_id,
        date=data.date,
        note=data.note,
        created_by=ctx["user"].id,
    )

    return {
        "id": transaction.id,
        "type": transaction.type.value if isinstance(transaction.type, TransactionType) else transaction.type,
        "category": transaction.category.value if transaction.category and isinstance(transaction.category, ExpenseCategory) else transaction.category,
        "amount": str(transaction.amount),
        "order_id": transaction.order_id,
        "supplier_id": transaction.supplier_id,
        "date": transaction.date.isoformat() if transaction.date else None,
        "note": transaction.note,
        "created_at": transaction.created_at.isoformat() if transaction.created_at else None,
    }


@router.put("/{transaction_id}")
async def update_transaction(
    transaction_id: int,
    data: ExpenseUpdate,
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(require_permission("finance", "write")),
):
    """修改支出记录"""
    service = TransactionService(db)
    transaction = await service.update_transaction(
        transaction_id=transaction_id,
        amount=data.amount,
        category=data.category,
        note=data.note,
    )

    return {
        "id": transaction.id,
        "amount": str(transaction.amount),
        "category": transaction.category.value if transaction.category and isinstance(transaction.category, ExpenseCategory) else transaction.category,
        "note": transaction.note,
    }


@router.get("/summary")
async def get_transaction_summary(
    start_date: date = Query(...),
    end_date: date = Query(...),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(require_permission("finance", "read")),
):
    """收支汇总统计"""
    service = TransactionService(db)
    summary = await service.get_summary(start_date, end_date)

    return {
        "income_total": str(summary["income_total"]),
        "expense_total": str(summary["expense_total"]),
        "net_amount": str(summary["net_amount"]),
        "by_category": {k: str(v) for k, v in summary["by_category"].items()},
    }
