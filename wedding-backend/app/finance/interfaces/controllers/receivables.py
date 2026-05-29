"""
应收账款 API
"""
from __future__ import annotations
from datetime import date, datetime
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
        start_datetime = datetime.combine(date_start, datetime.min.time())
    if date_end:
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
            "total_amount": str(item.total_amount),
            "received_amount": str(item.received_amount),
            "remaining_amount": str(item.remaining_amount),
            "status": item.status.value if isinstance(item.status, ReceivableStatus) else item.status,
            "due_date": item.due_date.isoformat() if item.due_date else None,
            "is_overdue": item.is_overdue,
            "overdue_days": item.overdue_days,
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

    # 获取关联订单信息
    order_no = None
    customer_name = None
    customer_phone = None
    sale_name = None

    if receivable.order:
        order_no = receivable.order.order_no
        if hasattr(receivable.order, 'customer') and receivable.order.customer:
            customer_name = receivable.order.customer.name
            customer_phone = receivable.order.customer.phone
        if hasattr(receivable.order, 'sale') and receivable.order.sale:
            sale_name = receivable.order.sale.name

    return {
        "id": receivable.id,
        "order_id": receivable.order_id,
        "order_no": order_no,
        "customer_name": customer_name,
        "customer_phone": customer_phone,
        "sale_name": sale_name,
        "total_amount": str(receivable.total_amount),
        "received_amount": str(receivable.received_amount),
        "remaining_amount": str(receivable.remaining_amount),
        "status": receivable.status.value if isinstance(receivable.status, ReceivableStatus) else receivable.status,
        "due_date": receivable.due_date.isoformat() if receivable.due_date else None,
        "is_overdue": receivable.is_overdue,
        "overdue_days": receivable.overdue_days,
        "created_at": receivable.created_at.isoformat() if receivable.created_at else None,
        "updated_at": receivable.updated_at.isoformat() if receivable.updated_at else None,
        # 获取收款记录
        "payments": [],  # TODO: 实现收款记录查询
    }
