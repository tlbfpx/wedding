"""Cashflow controller."""
from __future__ import annotations
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import require_permission
from app.dashboard.domain.value_objects import PeriodType
from app.dashboard.application.services.cashflow_service import CashflowService

router = APIRouter()


@router.get("/cashflow")
async def get_cashflow_metrics(
    period: PeriodType = Query(PeriodType.MONTH, description="Statistics period"),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(require_permission("dashboard", "read"))
):
    """Get cashflow and receivables metrics."""
    scope = ctx.get("scope", "all")
    user_id = ctx["user"].id

    return await CashflowService.get_metrics(
        period=period,
        scope=scope,
        user_id=user_id,
        db=db
    )
