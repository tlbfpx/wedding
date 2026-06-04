"""Team efficiency controller."""
from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import require_permission
from app.dashboard.domain.value_objects import PeriodType
from app.dashboard.application.services.team_efficiency_service import TeamEfficiencyService

router = APIRouter()


@router.get("/team-efficiency")
async def get_team_efficiency_metrics(
    period: PeriodType = Query(PeriodType.MONTH, description="Statistics period"),
    team: Optional[str] = Query(None, description="Team filter"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(require_permission("dashboard", "read"))
):
    """Get team efficiency metrics."""
    scope = ctx.get("scope", "all")
    user_id = ctx["user"].id

    return await TeamEfficiencyService.get_metrics(
        period=period,
        team=team,
        page=page,
        page_size=page_size,
        scope=scope,
        user_id=user_id,
        db=db
    )
