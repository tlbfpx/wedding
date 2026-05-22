from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy import select, func, and_, extract
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Event, EventResource, StaffSchedule
from app.models.event import EventStatus
from app.utils.errors import AppException


class EventService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_events(
        self,
        month: Optional[str],
        date_start: Optional[date],
        date_end: Optional[date],
        status: Optional[EventStatus],
        planner_id: Optional[int],
        venue_id: Optional[int],
        page: int,
        page_size: int,
    ) -> tuple[list[dict], int]:
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

        total_result = await self.db.execute(select(func.count()).select_from(query.subquery()))
        total = total_result.scalar_one()

        offset = (page - 1) * page_size
        query = query.order_by(Event.date.desc()).offset(offset).limit(page_size)
        result = await self.db.execute(query)
        events = result.scalars().all()

        items = [await _event_to_dict(e, self.db) for e in events]
        return items, total

    async def get_event_detail(self, event_id: int) -> dict:
        result = await self.db.execute(select(Event).where(Event.id == event_id))
        event = result.scalar_one_or_none()
        if not event:
            raise AppException(404, "NOT_FOUND", "活动不存在")

        resources_result = await self.db.execute(
            select(EventResource).where(EventResource.event_id == event_id)
        )
        resources = resources_result.scalars().all()

        staff_result = await self.db.execute(
            select(StaffSchedule).where(StaffSchedule.event_id == event_id)
        )
        staff = staff_result.scalars().all()

        return {
            **await _event_to_dict(event, self.db),
            "resources": [_resource_to_dict(r) for r in resources],
            "staff": [_staff_schedule_to_dict(s) for s in staff],
        }

    async def create_event(self, data) -> tuple[dict, object]:
        event_date = data.date
        if not event_date and data.event_date:
            event_date = date.fromisoformat(data.event_date)

        if not event_date:
            raise AppException(400, "MISSING_DATE", "活动日期不能为空")

        conflicts = await self._detect_conflicts(
            venue_id=data.venue_id,
            date=event_date,
            staff_ids=None,
            exclude_event_id=None,
        )
        if conflicts:
            raise AppException(409, "CONFLICT_DETECTED", f"存在冲突: {conflicts}")

        event = Event(
            order_id=data.order_id,
            title=data.title,
            date=event_date,
            venue_id=data.venue_id,
            planner_id=data.planner_id,
            status=EventStatus.draft,
            note=data.note,
        )
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(event)

        result = await _event_to_dict(event, self.db)
        return result, event

    async def update_event(self, event_id: int, data) -> tuple[dict, list[str]]:
        result = await self.db.execute(select(Event).where(Event.id == event_id))
        event = result.scalar_one_or_none()
        if not event:
            raise AppException(404, "NOT_FOUND", "活动不存在")

        # Check for conflicts only on date/venue changes
        new_date = data.date or event.date
        new_venue = data.venue_id if data.venue_id is not None else event.venue_id
        if data.date is not None or data.venue_id is not None:
            conflicts = await self._detect_conflicts(
                venue_id=new_venue,
                date=new_date,
                staff_ids=None,
                exclude_event_id=event_id,
            )
            if conflicts:
                raise AppException(409, "CONFLICT_DETECTED", f"存在冲突: {conflicts}")

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(event, key, value)

        await self.db.commit()
        await self.db.refresh(event)

        result = await _event_to_dict(event, self.db)
        return result, list(update_data.keys())

    async def query_staff_schedule(
        self,
        date_param: Optional[date],
        staff_id: Optional[int],
        event_id: Optional[int],
    ) -> list[dict]:
        query = select(StaffSchedule)

        if date_param:
            query = query.where(StaffSchedule.date == date_param)
        if staff_id:
            query = query.where(StaffSchedule.staff_id == staff_id)
        if event_id:
            query = query.where(StaffSchedule.event_id == event_id)

        result = await self.db.execute(query.order_by(StaffSchedule.date))
        schedules = result.scalars().all()
        return [_staff_schedule_to_dict(s) for s in schedules]

    async def check_conflicts(
        self,
        venue_id: Optional[int],
        date_val: date,
        staff_ids: Optional[list[int]],
        exclude_event_id: Optional[int],
    ) -> dict:
        conflicts = await self._detect_conflicts(
            venue_id=venue_id,
            date=date_val,
            staff_ids=staff_ids,
            exclude_event_id=exclude_event_id,
        )
        return {"has_conflicts": bool(conflicts), "conflicts": conflicts}

    async def add_resource(self, event_id: int, data) -> tuple[dict, int]:
        event_result = await self.db.execute(select(Event).where(Event.id == event_id))
        if not event_result.scalar_one_or_none():
            raise AppException(404, "NOT_FOUND", "活动不存在")

        resource = EventResource(
            event_id=event_id,
            resource_type=data.resource_type,
            resource_id=data.resource_id,
            quantity=data.quantity,
            note=data.note,
        )
        self.db.add(resource)
        await self.db.commit()
        await self.db.refresh(resource)

        return _resource_to_dict(resource), resource.id

    async def remove_resource(self, event_id: int, resource_id: int) -> None:
        result = await self.db.execute(
            select(EventResource).where(
                EventResource.id == resource_id,
                EventResource.event_id == event_id,
            )
        )
        resource = result.scalar_one_or_none()
        if not resource:
            raise AppException(404, "NOT_FOUND", "资源不存在")

        await self.db.delete(resource)
        await self.db.commit()

    async def _detect_conflicts(
        self,
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
            result = await self.db.execute(venue_query)
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
            result = await self.db.execute(staff_query)
            staff_conflicts = result.scalars().all()
            if staff_conflicts:
                conflict_ids = list(set(s.staff_id for s in staff_conflicts))
                conflicts.append(f"员工冲突 staff_ids: {conflict_ids}")

        return conflicts


# ── Helpers ──────────────────────────────────────────────────────────────────

async def _event_to_dict(e: Event, db: Optional[AsyncSession] = None) -> dict:
    venue_name = None
    if e.venue_id and db:
        from app.models.event import Venue
        vresult = await db.execute(select(Venue).where(Venue.id == e.venue_id))
        venue = vresult.scalar_one_or_none()
        if venue:
            venue_name = venue.name

    planner_name = None
    if e.planner_id and db:
        from app.models.user import User
        presult = await db.execute(select(User).where(User.id == e.planner_id))
        planner = presult.scalar_one_or_none()
        if planner:
            planner_name = planner.name

    return {
        "id": e.id,
        "order_id": e.order_id,
        "title": e.title,
        "event_date": str(e.date) if e.date else None,
        "date": str(e.date) if e.date else None,
        "start_time": str(e.start_time) if e.start_time else None,
        "end_time": str(e.end_time) if e.end_time else None,
        "venue_id": e.venue_id,
        "venue": {"id": e.venue_id, "name": venue_name} if e.venue_id else None,
        "status": e.status.value,
        "planner_id": e.planner_id,
        "planner": {"id": e.planner_id, "name": planner_name} if e.planner_id else None,
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
