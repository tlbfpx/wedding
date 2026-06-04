"""Health controller for business health API."""
from __future__ import annotations
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import require_permission
from app.dashboard.domain.value_objects import PeriodType, CompareToType
from app.dashboard.application.services.health_service import HealthService
from app.dashboard.domain.dtos import HealthMetrics

router = APIRouter()


@router.get("/health", response_model=HealthMetrics)
async def get_health_metrics(
    period: PeriodType = Query(PeriodType.MONTH, description="Statistics period"),
    compare_to: Optional[CompareToType] = Query(None, description="Comparison period"),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(require_permission("dashboard", "read"))
) -> HealthMetrics:
    """Get business health metrics.

    Returns revenue, orders, avg order value, sign rate, and gross profit
    with optional trend comparison.
    """
    scope = ctx.get("scope", "all")
    user_id = ctx["user"].id

    return await HealthService.get_metrics(
        period=period,
        compare_to=compare_to,
        scope=scope,
        user_id=user_id,
        db=db
    )
