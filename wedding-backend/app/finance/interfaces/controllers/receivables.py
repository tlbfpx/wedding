"""
应收账款 API
"""
from __future__ import annotations
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import require_permission
from app.finance.application.services import ReceivableService
from app.finance.domain.entities.enums import ReceivableStatus
from app.utils.pagination import PageResponse

router = APIRouter()


@router.get("")
async def list_receivables(
    status: Optional[ReceivableStatus] = Query(None),
    sale_id: Optional[int] = Query(None),
    date_start: Optional[date] = Query(None),
    date_end: Optional[date] = Query(None),
    keyword: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(require_permission("finance", "read")),
):
    """应收账款列表"""
    service = ReceivableService(db)

    # 将日期转换为 datetime
    start_datetime = None
    end_datetime = None
    if date_start:
        from datetime import datetime
        start_datetime = datetime.combine(date_start, datetime.min.time())
    if date_end:
        from datetime import datetime
        end_datetime = datetime.combine(date_end, datetime.max.time())

    items, total = await service.repo.list(
        status=status,
        sale_id=sale_id,
        date_start=start_datetime,
        date_end=end_datetime,
        keyword=keyword,
        offset=(page - 1) * page_size,
        limit=page_size,
    )

    # 序列化结果
    result_items = []
    for item in items:
        result_items.append({
            "id": item.id,
            "order_id": item.order_id,
            "order_no": item.order.order_no if hasattr(item, 'order') and item.order else None,
            "customer_name": item.order.customer.name if hasattr(item, 'order') and item.order and hasattr(item.order, 'customer') else None,
            "sale_name": item.order.sale.name if hasattr(item, 'order') and item.order and hasattr(item.order, 'sale') else None,
            "total_amount": str(item.total_amount),
            "received_amount": str(item.received_amount),
            "remaining_amount": str(item.remaining_amount),
            "status": item.status.value if isinstance(item.status, ReceivableStatus) else item.status,
            "due_date": item.due_date.isoformat() if item.due_date else None,
            "is_overdue": item.is_overdue,
            "created_at": item.created_at.isoformat() if item.created_at else None,
        })

    return PageResponse(
        items=result_items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/overdue")
async def list_overdue_receivables(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(require_permission("finance", "read")),
):
    """逾期应收列表"""
    service = ReceivableService(db)
    receivables = await service.check_overdue_receivables()

    # 分页
    start = (page - 1) * page_size
    end = start + page_size
    items = receivables[start:end]

    result_items = []
    for item in items:
        result_items.append({
            "id": item.id,
            "order_id": item.order_id,
            "order_no": item.order.order_no if hasattr(item, 'order') and item.order else None,
            "customer_name": item.order.customer.name if hasattr(item, 'order') and item.order and hasattr(item.order, 'customer') else None,
            "total_amount": str(item.total_amount),
            "received_amount": str(item.received_amount),
            "remaining_amount": str(item.remaining_amount),
            "status": item.status.value if isinstance(item.status, ReceivableStatus) else item.status,
            "due_date": item.due_date.isoformat() if item.due_date else None,
            "overdue_days": item.overdue_days,
        })

    return PageResponse(
        items=result_items,
        total=len(receivables),
        page=page,
        page_size=page_size,
        total_pages=(len(receivables) + page_size - 1) // page_size,
    )


@router.get("/{receivable_id}")
async def get_receivable(
    receivable_id: int,
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(require_permission("finance", "read")),
):
    """应收详情"""
    service = ReceivableService(db)
    receivable = await service.repo.get_with_details(receivable_id)

    if not receivable:
        from app.utils.errors import AppException
        raise AppException(404, "RECEIVABLE_NOT_FOUND", "应收记录不存在")

    return {
        "id": receivable.id,
        "order_id": receivable.order_id,
        "order_no": receivable.order.order_no if hasattr(receivable, 'order') and receivable.order else None,
        "customer_name": receivable.order.customer.name if hasattr(receivable, 'order') and receivable.order and hasattr(receivable.order, 'customer') else None,
        "customer_phone": receivable.order.customer.phone if hasattr(receivable, 'order') and receivable.order and hasattr(receivable.order, 'customer') else None,
        "sale_name": receivable.order.sale.name if hasattr(receivable, 'order') and receivable.order and hasattr(receivable.order, 'sale') else None,
        "total_amount": str(receivable.total_amount),
        "received_amount": str(receivable.received_amount),
        "remaining_amount": str(receivable.remaining_amount),
        "status": receivable.status.value if isinstance(receivable.status, ReceivableStatus) else receivable.status,
        "due_date": receivable.due_date.isoformat() if receivable.due_date else None,
        "is_overdue": receivable.is_overdue,
        "overdue_days": receivable.overdue_days,
        "created_at": receivable.created_at.isoformat() if receivable.created_at else None,
        "updated_at": receivable.updated_at.isoformat() if receivable.updated_at else None,
    }
