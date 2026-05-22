from __future__ import annotations
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.database import get_db
from app.models import Venue, Event
from app.models.event import EventStatus
from app.middleware.auth import get_current_user
from app.models.user import User
from app.utils.errors import AppException
from app.utils.pagination import PageResponse
from app.middleware.logging import log_operation

router = APIRouter()


# ── Schemas ──────────────────────────────────────────────────────────────────

class VenueCreate(BaseModel):
    name: str
    address: Optional[str] = None
    capacity: Optional[int] = None
    contact: Optional[str] = None
    phone: Optional[str] = None
    price: Optional[float] = None
    note: Optional[str] = None


class VenueUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    capacity: Optional[int] = None
    contact: Optional[str] = None
    phone: Optional[str] = None
    price: Optional[float] = None
    note: Optional[str] = None


# ── Routes ───────────────────────────────────────────────────────────────────

@router.get("")
async def list_venues(
    keyword: Optional[str] = Query(None),
    capacity_min: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = select(Venue)

    if keyword:
        query = query.where(
            (Venue.name.like(f"%{keyword}%"))
            | (Venue.address.like(f"%{keyword}%"))
        )
    if capacity_min is not None:
        query = query.where(Venue.capacity >= capacity_min)

    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar_one()

    offset = (page - 1) * page_size
    query = query.order_by(Venue.created_at.desc()).offset(offset).limit(page_size)
    result = await db.execute(query)
    venues = result.scalars().all()

    return PageResponse(
        items=[_venue_to_dict(v) for v in venues],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.post("")
async def create_venue(
    body: VenueCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    existing = await db.execute(select(Venue).where(Venue.name == body.name))
    if existing.scalar_one_or_none():
        raise AppException(400, "DUPLICATE_NAME", "场地名称已存在")

    venue = Venue(
        name=body.name,
        address=body.address,
        capacity=body.capacity,
        contact=body.contact,
        phone=body.phone,
        price=body.price,
        note=body.note,
    )
    db.add(venue)
    await db.commit()
    await db.refresh(venue)

    await log_operation(db, user.id, request, {"venue_id": venue.id, "name": venue.name})
    return _venue_to_dict(venue)


@router.put("/{venue_id}")
async def update_venue(
    venue_id: int,
    body: VenueUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Venue).where(Venue.id == venue_id))
    venue = result.scalar_one_or_none()
    if not venue:
        raise AppException(404, "NOT_FOUND", "场地不存在")

    if body.name and body.name != venue.name:
        existing = await db.execute(select(Venue).where(Venue.name == body.name))
        if existing.scalar_one_or_none():
            raise AppException(400, "DUPLICATE_NAME", "场地名称已存在")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(venue, key, value)

    await db.commit()
    await db.refresh(venue)

    await log_operation(db, user.id, request, {"venue_id": venue_id, "updated_fields": list(update_data.keys())})
    return _venue_to_dict(venue)


@router.get("/{venue_id}/availability")
async def check_availability(
    venue_id: int,
    date_start: date = Query(...),
    date_end: date = Query(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Venue).where(Venue.id == venue_id))
    if not result.scalar_one_or_none():
        raise AppException(404, "NOT_FOUND", "场地不存在")

    events_result = await db.execute(
        select(Event).where(
            Event.venue_id == venue_id,
            Event.date >= date_start,
            Event.date <= date_end,
            Event.status != EventStatus.cancelled,
        ).order_by(Event.date)
    )
    events = events_result.scalars().all()

    booked_dates = [str(e.date) for e in events]

    return {
        "venue_id": venue_id,
        "date_start": str(date_start),
        "date_end": str(date_end),
        "booked_dates": booked_dates,
        "available": len(booked_dates) == 0,
    }


# ── Helpers ──────────────────────────────────────────────────────────────────

def _venue_to_dict(v: Venue) -> dict:
    return {
        "id": v.id,
        "name": v.name,
        "address": v.address,
        "capacity": v.capacity,
        "contact": v.contact,
        "phone": v.phone,
        "price": float(v.price) if v.price else None,
        "note": v.note,
        "created_at": v.created_at.isoformat() if v.created_at else None,
        "updated_at": v.updated_at.isoformat() if v.updated_at else None,
    }
