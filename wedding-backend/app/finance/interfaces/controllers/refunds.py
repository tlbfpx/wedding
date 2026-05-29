"""
退款 API
"""
from __future__ import annotations
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import require_permission
from app.finance.application.services import RefundService
from app.finance.domain.entities.enums import RefundStatus
from app.utils.pagination import PageResponse

router = APIRouter()


class RefundCreate(BaseModel):
    """退款申请请求"""
    order_id: int
    amount: float
    reason: str
    note: Optional[str] = None


class RefundUpdateStatus(BaseModel):
    """退款状态更新请求"""
    status: RefundStatus


@router.post("")
async def create_refund(
    data: RefundCreate,
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(require_permission("finance", "write")),
):
    """申请退款"""
    service = RefundService(db)
    refund = await service.request_refund(
        order_id=data.order_id,
        amount=data.amount,
        reason=data.reason,
        user_id=ctx["user"].id,
        note=data.note,
    )

    return {
        "id": refund.id,
        "order_id": refund.order_id,
        "order_no": refund.order.order_no if hasattr(refund, 'order') and refund.order else None,
        "amount": str(refund.amount),
        "reason": refund.reason,
        "status": refund.status.value if isinstance(refund.status, RefundStatus) else refund.status,
        "approval_id": refund.approval_id,
        "created_at": refund.created_at.isoformat() if refund.created_at else None,
    }


@router.get("")
async def list_refunds(
    order_id: Optional[int] = Query(None),
    status: Optional[RefundStatus] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(require_permission("finance", "read")),
):
    """退款记录列表"""
    service = RefundService(db)
    items, total = await service.list_refunds(
        order_id=order_id,
        status=status,
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
            "reason": item.reason,
            "status": item.status.value if isinstance(item.status, RefundStatus) else item.status,
            "approval_id": item.approval_id,
            "approved_by": item.approved_by,
            "approved_at": item.approved_at.isoformat() if item.approved_at else None,
            "refunded_at": item.refunded_at.isoformat() if item.refunded_at else None,
            "created_at": item.created_at.isoformat() if item.created_at else None,
        })

    return PageResponse(
        items=result_items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/{refund_id}")
async def get_refund(
    refund_id: int,
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(require_permission("finance", "read")),
):
    """退款详情"""
    service = RefundService(db)
    refund = await service.get_refund(refund_id)

    return {
        "id": refund.id,
        "order_id": refund.order_id,
        "order_no": refund.order.order_no if hasattr(refund, 'order') and refund.order else None,
        "amount": str(refund.amount),
        "reason": refund.reason,
        "status": refund.status.value if isinstance(refund.status, RefundStatus) else refund.status,
        "approval_id": refund.approval_id,
        "approved_by": refund.approved_by,
        "approved_at": refund.approved_at.isoformat() if refund.approved_at else None,
        "refunded_at": refund.refunded_at.isoformat() if refund.refunded_at else None,
        "note": refund.note,
        "created_at": refund.created_at.isoformat() if refund.created_at else None,
        "created_by": refund.created_by,
    }


@router.put("/{refund_id}/status")
async def update_refund_status(
    refund_id: int,
    data: RefundUpdateStatus,
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(require_permission("finance", "write")),
):
    """更新退款状态（标记已退款）"""
    service = RefundService(db)

    if data.status == RefundStatus.refunded:
        refund = await service.confirm_refund(refund_id)
    else:
        from app.utils.errors import AppException
        raise AppException(400, "INVALID_STATUS", "不支持的状态变更")

    return {
        "id": refund.id,
        "status": refund.status.value if isinstance(refund.status, RefundStatus) else refund.status,
    }
