"""Decision support controller."""
from __future__ import annotations
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import require_permission
from app.dashboard.domain.value_objects import PeriodType, DecisionDimension
from app.dashboard.application.services.decision_support_service import DecisionSupportService

router = APIRouter()


@router.get("/decision-support")
async def get_decision_support_metrics(
    period: PeriodType = Query(PeriodType.MONTH, description="Statistics period"),
    dimension: DecisionDimension = Query(DecisionDimension.SOURCE, description="Analysis dimension"),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(require_permission("dashboard", "read"))
):
    """Get decision support metrics."""
    scope = ctx.get("scope", "all")
    user_id = ctx["user"].id

    # Check if user has read_all permission
    if scope != "all":
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Requires dashboard:read_all permission")

    return await DecisionSupportService.get_metrics(
        period=period,
        dimension=dimension,
        scope=scope,
        user_id=user_id,
        db=db
    )
