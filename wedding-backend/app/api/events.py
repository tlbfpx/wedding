from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select, func, and_, delete, extract
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.database import get_db
from app.models import Event, EventResource, StaffSchedule
from app.models.event import EventStatus, ResourceType, ScheduleStatus
from app.middleware.auth import get_current_user
from app.models.user import User
from app.utils.errors import AppException
from app.utils.pagination import PageResponse
from app.middleware.logging import log_operation

router = APIRouter()


# ── Schemas ──────────────────────────────────────────────────────────────────

class EventCreate(BaseModel):
    order_id: Optional[int] = None
    title: str
    date: date
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    venue_id: Optional[int] = None
    planner_id: Optional[int] = None
    note: Optional[str] = None


class EventUpdate(BaseModel):
    title: Optional[str] = None
    date: Optional[date] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    venue_id: Optional[int] = None
    planner_id: Optional[int] = None
    status: Optional[EventStatus] = None
    note: Optional[str] = None


class ResourceInput(BaseModel):
    resource_type: ResourceType
    resource_id: int
    quantity: int = 1
    note: Optional[str] = None


class ConflictCheck(BaseModel):
    venue_id: Optional[int] = None
    date: date
    staff_ids: Optional[list[int]] = None
    exclude_event_id: Optional[int] = None


# ── Event Routes ─────────────────────────────────────────────────────────────

@router.get("/")
async def list_events(
    month: Optional[str] = Query(None, description="YYYY-MM format"),
    date_start: Optional[date] = Query(None),
    date_end: Optional[date] = Query(None),
    status: Optional[EventStatus] = Query(None),
    planner_id: Optional[int] = Query(None),
    venue_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = select(Event)

    if month:
        year, m = month.split("-")
        query = query.where(
            and_(
                extract("year", Event.date) == int(year),
                extract("month", Event.date) == int(m),
            )
        )
    if date_start:
        query = query.where(Event.date >= date_start)
    if date_end:
        query = query.where(Event.date <= date_end)
    if status:
        query = query.where(Event.status == status)
    if planner_id:
        query = query.where(Event.planner_id == planner_id)
    if venue_id:
        query = query.where(Event.venue_id == venue_id)

    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar_one()

    offset = (page - 1) * page_size
    query = query.order_by(Event.date.desc()).offset(offset).limit(page_size)
    result = await db.execute(query)
    events = result.scalars().all()

    return PageResponse(
        items=[_event_to_dict(e) for e in events],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/{event_id}")
async def get_event(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise AppException(404, "NOT_FOUND", "活动不存在")

    resources_result = await db.execute(
        select(EventResource).where(EventResource.event_id == event_id)
    )
    resources = resources_result.scalars().all()

    staff_result = await db.execute(
        select(StaffSchedule).where(StaffSchedule.event_id == event_id)
    )
    staff = staff_result.scalars().all()

    return {
        **_event_to_dict(event),
        "resources": [_resource_to_dict(r) for r in resources],
        "staff": [_staff_schedule_to_dict(s) for s in staff],
    }


@router.post("/")
async def create_event(
    body: EventCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    conflicts = await _detect_conflicts(
        db=db,
        venue_id=body.venue_id,
        date=body.date,
        staff_ids=None,
        exclude_event_id=None,
    )
    if conflicts:
        raise AppException(409, "CONFLICT_DETECTED", f"存在冲突: {conflicts}")

    event = Event(
        order_id=body.order_id,
        title=body.title,
        date=body.date,
        venue_id=body.venue_id,
        planner_id=body.planner_id,
        status=EventStatus.draft,
        note=body.note,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)

    await log_operation(db, user.id, request, {"event_id": event.id, "title": event.title})
    return _event_to_dict(event)


@router.put("/{event_id}")
async def update_event(
    event_id: int,
    body: EventUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise AppException(404, "NOT_FOUND", "活动不存在")

    # Check for conflicts only on date/venue changes
    new_date = body.date or event.date
    new_venue = body.venue_id if body.venue_id is not None else event.venue_id
    if body.date is not None or body.venue_id is not None:
        conflicts = await _detect_conflicts(
            db=db,
            venue_id=new_venue,
            date=new_date,
            staff_ids=None,
            exclude_event_id=event_id,
        )
        if conflicts:
            raise AppException(409, "CONFLICT_DETECTED", f"存在冲突: {conflicts}")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(event, key, value)

    await db.commit()
    await db.refresh(event)

    await log_operation(db, user.id, request, {"event_id": event_id, "updated_fields": list(update_data.keys())})
    return _event_to_dict(event)


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
    event_result = await db.execute(select(Event).where(Event.id == event_id))
    if not event_result.scalar_one_or_none():
        raise AppException(404, "NOT_FOUND", "活动不存在")

    resource = EventResource(
        event_id=event_id,
        resource_type=body.resource_type,
        resource_id=body.resource_id,
        quantity=body.quantity,
        note=body.note,
    )
    db.add(resource)
    await db.commit()
    await db.refresh(resource)

    await log_operation(db, user.id, request, {"event_id": event_id, "resource_id": resource.id})
    return _resource_to_dict(resource)


@router.delete("/{event_id}/resources/{resource_id}")
async def remove_resource(
    event_id: int,
    resource_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(EventResource).where(
            EventResource.id == resource_id,
            EventResource.event_id == event_id,
        )
    )
    resource = result.scalar_one_or_none()
    if not resource:
        raise AppException(404, "NOT_FOUND", "资源不存在")

    await db.delete(resource)
    await db.commit()

    await log_operation(db, user.id, request, {"event_id": event_id, "removed_resource_id": resource_id})
    return {"message": "资源已移除"}


# ── Staff Schedule Route ─────────────────────────────────────────────────────

@router.get("/staff-schedule")
async def query_staff_schedule(
    date_param: Optional[date] = Query(None, alias="date"),
    staff_id: Optional[int] = Query(None),
    event_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = select(StaffSchedule)

    if date_param:
        query = query.where(StaffSchedule.date == date_param)
    if staff_id:
        query = query.where(StaffSchedule.staff_id == staff_id)
    if event_id:
        query = query.where(StaffSchedule.event_id == event_id)

    result = await db.execute(query.order_by(StaffSchedule.date))
    schedules = result.scalars().all()
    return [_staff_schedule_to_dict(s) for s in schedules]


# ── Conflict Check Route ─────────────────────────────────────────────────────

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

    conflicts = await _detect_conflicts(
        db=db,
        venue_id=venue_id,
        date=date,
        staff_ids=parsed_staff_ids,
        exclude_event_id=exclude_event_id,
    )
    return {"has_conflicts": bool(conflicts), "conflicts": conflicts}


# ── Helpers ──────────────────────────────────────────────────────────────────

async def _detect_conflicts(
    db: AsyncSession,
    venue_id: Optional[int],
    date: date,
    staff_ids: Optional[list[int]],
    exclude_event_id: Optional[int],
) -> list[str]:
    conflicts = []

    # Venue conflict check
    if venue_id:
        venue_query = select(Event).where(
            Event.venue_id == venue_id,
            Event.date == date,
            Event.status != EventStatus.cancelled,
        )
        if exclude_event_id:
            venue_query = venue_query.where(Event.id != exclude_event_id)
        result = await db.execute(venue_query)
        venue_events = result.scalars().all()
        if venue_events:
            names = ", ".join(e.title for e in venue_events)
            conflicts.append(f"场地已被占用: {names}")

    # Staff conflict check
    if staff_ids:
        staff_query = select(StaffSchedule).where(
            StaffSchedule.staff_id.in_(staff_ids),
            StaffSchedule.date == date,
        )
        if exclude_event_id:
            staff_query = staff_query.where(StaffSchedule.event_id != exclude_event_id)
        result = await db.execute(staff_query)
        staff_conflicts = result.scalars().all()
        if staff_conflicts:
            conflict_ids = list(set(s.staff_id for s in staff_conflicts))
            conflicts.append(f"员工冲突 staff_ids: {conflict_ids}")

    return conflicts


def _event_to_dict(e: Event) -> dict:
    return {
        "id": e.id,
        "order_id": e.order_id,
        "title": e.title,
        "date": str(e.date) if e.date else None,
        "start_time": str(e.start_time) if e.start_time else None,
        "end_time": str(e.end_time) if e.end_time else None,
        "venue_id": e.venue_id,
        "status": e.status.value,
        "planner_id": e.planner_id,
        "note": e.note,
        "created_at": e.created_at.isoformat() if e.created_at else None,
        "updated_at": e.updated_at.isoformat() if e.updated_at else None,
    }


def _resource_to_dict(r: EventResource) -> dict:
    return {
        "id": r.id,
        "event_id": r.event_id,
        "resource_type": r.resource_type.value,
        "resource_id": r.resource_id,
        "quantity": r.quantity,
        "note": r.note,
    }


def _staff_schedule_to_dict(s: StaffSchedule) -> dict:
    return {
        "id": s.id,
        "staff_id": s.staff_id,
        "event_id": s.event_id,
        "role": s.role,
        "date": str(s.date) if s.date else None,
        "status": s.status.value,
    }
