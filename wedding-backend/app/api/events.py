from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import EventResource
from app.models.event import EventStatus
from app.middleware.auth import get_current_user
from app.models.user import User
from app.utils.pagination import PageResponse
from app.middleware.logging import log_operation
from app.schemas.event import EventCreate, EventUpdate, ResourceInput, ConflictCheck
from app.services.event_service import EventService

router = APIRouter()


# ── Event Routes ─────────────────────────────────────────────────────────────

@router.get("")
async def list_events(
    month: Optional[str] = Query(None, description="YYYY-MM format"),
    date_start: Optional[date] = Query(None),
    date_end: Optional[date] = Query(None),
    status: Optional[EventStatus] = Query(None),
    planner_id: Optional[int] = Query(None),
    venue_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    svc = EventService(db)
    items, total = await svc.list_events(
        month=month,
        date_start=date_start,
        date_end=date_end,
        status=status,
        planner_id=planner_id,
        venue_id=venue_id,
        page=page,
        page_size=page_size,
    )
    return PageResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


# ── Static routes BEFORE parameterized /{event_id} ──────────────────────────

@router.get("/staff-schedule")
async def query_staff_schedule(
    date_param: Optional[date] = Query(None, alias="date"),
    staff_id: Optional[int] = Query(None),
    event_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    svc = EventService(db)
    return await svc.query_staff_schedule(
        date_param=date_param,
        staff_id=staff_id,
        event_id=event_id,
    )


@router.get("/conflicts")
async def check_conflicts(
    venue_id: Optional[int] = Query(None),
    date: date = Query(...),
    staff_ids: Optional[str] = Query(None, description="Comma-separated staff IDs"),
    exclude_event_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    parsed_staff_ids = None
    if staff_ids:
        parsed_staff_ids = [int(sid.strip()) for sid in staff_ids.split(",") if sid.strip()]

    svc = EventService(db)
    return await svc.check_conflicts(
        venue_id=venue_id,
        date_val=date,
        staff_ids=parsed_staff_ids,
        exclude_event_id=exclude_event_id,
    )


# ── Parameterized routes ────────────────────────────────────────────────────

@router.get("/{event_id}")
async def get_event(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    svc = EventService(db)
    return await svc.get_event_detail(event_id)


@router.post("")
async def create_event(
    body: EventCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    svc = EventService(db)
    result, event = await svc.create_event(body)
    await log_operation(db, user.id, request, {"event_id": event.id, "title": event.title})
    return result


@router.put("/{event_id}")
async def update_event(
    event_id: int,
    body: EventUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    svc = EventService(db)
    result, updated_fields = await svc.update_event(event_id, body)
    await log_operation(db, user.id, request, {"event_id": event_id, "updated_fields": updated_fields})
    return result


# ── Resource Routes ──────────────────────────────────────────────────────────

@router.get("/{event_id}/resources")
async def list_resources(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(EventResource).where(EventResource.event_id == event_id)
    )
    resources = result.scalars().all()
    return [_resource_to_dict(r) for r in resources]


@router.post("/{event_id}/resources")
async def add_resource(
    event_id: int,
    body: ResourceInput,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    svc = EventService(db)
    result, resource_id = await svc.add_resource(event_id, body)
    await log_operation(db, user.id, request, {"event_id": event_id, "resource_id": resource_id})
    return result


@router.delete("/{event_id}/resources/{resource_id}")
async def remove_resource(
    event_id: int,
    resource_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    svc = EventService(db)
    await svc.remove_resource(event_id, resource_id)
    await log_operation(db, user.id, request, {"event_id": event_id, "removed_resource_id": resource_id})
    return {"message": "资源已移除"}


# ── Helpers ──────────────────────────────────────────────────────────────────

def _resource_to_dict(r: EventResource) -> dict:
    return {
        "id": r.id,
        "event_id": r.event_id,
        "resource_type": r.resource_type.value,
        "resource_id": r.resource_id,
        "quantity": r.quantity,
        "note": r.note,
    }
