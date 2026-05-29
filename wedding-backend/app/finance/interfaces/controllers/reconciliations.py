"""
对账 API
"""
from __future__ import annotations
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import require_permission
from app.finance.application.services import ReconciliationService
from app.utils.pagination import PageResponse

router = APIRouter()


class ReconciliationConfirm(BaseModel):
    """确认对账请求"""
    period: str
    notes: Optional[str] = None


@router.get("/report")
async def get_reconciliation_report(
    period: str = Query(...),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(require_permission("finance", "read")),
):
    """生成对账报表"""
    service = ReconciliationService(db)
    report = await service.generate_report(period)
    return report


@router.post("/confirm")
async def confirm_reconciliation(
    data: ReconciliationConfirm,
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(require_permission("finance", "approve")),
):
    """确认对账"""
    service = ReconciliationService(db)
    reconciliation = await service.confirm_reconciliation(
        period=data.period,
        notes=data.notes,
        user_id=ctx["user"].id,
    )

    return {
        "id": reconciliation.id,
        "period": reconciliation.period,
        "snapshot": reconciliation.snapshot,
        "confirmed_by": reconciliation.confirmed_by,
        "confirmed_at": reconciliation.confirmed_at.isoformat() if reconciliation.confirmed_at else None,
        "notes": reconciliation.notes,
    }


@router.get("/history")
async def get_reconciliation_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(require_permission("finance", "read")),
):
    """对账历史记录"""
    service = ReconciliationService(db)
    items, total = await service.get_history(page=page, page_size=page_size)

    result_items = []
    for item in items:
        result_items.append({
            "id": item.id,
            "period": item.period,
            "notes": item.notes,
            "confirmed_by": item.confirmed_by,
            "confirmed_at": item.confirmed_at.isoformat() if item.confirmed_at else None,
            "created_at": item.created_at.isoformat() if item.created_at else None,
        })

    return PageResponse(
        items=result_items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )
