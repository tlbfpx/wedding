"""Alerts controller."""
from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, Depends, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.database import get_db
from app.middleware.auth import require_permission
from app.dashboard.domain.value_objects import AlertLevel
from app.dashboard.application.services.alert_service import AlertService

router = APIRouter()


@router.get("/alerts")
async def get_alerts(
    level: Optional[AlertLevel] = Query(None, description="Filter by alert level"),
    type: Optional[str] = Query(None, description="Filter by alert type"),
    limit: int = Query(20, ge=1, le=100, description="Limit results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(require_permission("dashboard", "read"))
):
    """Get risk alerts."""
    scope = ctx.get("scope", "all")
    user_id = ctx["user"].id

    total, alerts = await AlertService.get_alerts(
        level=level,
        type_filter=type,
        limit=limit,
        offset=offset,
        scope=scope,
        user_id=user_id,
        db=db
    )

    # Count by level
    high_count = sum(1 for a in alerts if a.level == AlertLevel.HIGH)
    medium_count = sum(1 for a in alerts if a.level == AlertLevel.MEDIUM)
    low_count = sum(1 for a in alerts if a.level == AlertLevel.LOW)

    return {
        "high_count": high_count,
        "medium_count": medium_count,
        "low_count": low_count,
        "alerts": [
            {
                "id": a.id,
                "level": a.level.value,
                "type": a.type,
                "title": a.title,
                "detail": a.detail,
                "entity_type": a.entity_type,
                "entity_id": a.entity_id,
                "owner_id": a.owner_id,
                "owner_name": a.owner_name,
                "actions": a.actions,
                "created_at": a.created_at.isoformat()
            }
            for a in alerts
        ],
        "total": total
    }


@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: str,
    note: str = Body("", embed=True),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(require_permission("dashboard", "write"))
):
    """Mark alert as resolved."""
    user_id = ctx["user"].id

    success = await AlertService.mark_resolved(
        alert_id=alert_id,
        note=note,
        user_id=user_id,
        db=db
    )

    if not success:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Alert not found")

    return {
        "success": True,
        "resolved_at": datetime.utcnow().isoformat()
    }
