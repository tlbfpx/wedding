"""
Tests for event endpoints: /api/v1/events/* and /api/v1/venues/*
"""

import pytest
from datetime import date, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Venue


pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _create_venue(client: AsyncClient, headers: dict, **overrides) -> dict:
    import uuid
    payload = {
        "name": "场地-" + uuid.uuid4().hex[:6],
        "address": "某路123号",
        "capacity": 200,
        "contact": "张经理",
        "phone": "13600001111",
        "price": 15000.0,
    }
    payload.update(overrides)
    resp = await client.post("/api/v1/venues", headers=headers, json=payload)
    assert resp.status_code == 200
    return resp.json()


async def _create_event(
    client: AsyncClient, headers: dict, venue_id: int | None = None, **overrides
) -> dict:
    payload = {
        "title": "测试婚礼活动",
        "date": str(date.today() + timedelta(days=30)),
        "venue_id": venue_id,
    }
    payload.update(overrides)
    resp = await client.post("/api/v1/events", headers=headers, json=payload)
    assert resp.status_code == 200
    return resp.json()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

async def test_create_event(async_client: AsyncClient, auth_headers):
    """POST /api/v1/events creates a new event."""
    venue = await _create_venue(async_client, auth_headers)
    event = await _create_event(async_client, auth_headers, venue_id=venue["id"])
    assert event["title"] == "测试婚礼活动"
    assert event["status"] == "draft"
    assert event["venue_id"] == venue["id"]


async def test_list_events(async_client: AsyncClient, auth_headers):
    """GET /api/v1/events returns paginated list."""
    await _create_event(async_client, auth_headers)

    resp = await async_client.get("/api/v1/events", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1


async def test_venue_conflict_detection(async_client: AsyncClient, auth_headers):
    """
    Creating two events on the same date at the same venue triggers a conflict.
    """
    venue = await _create_venue(async_client, auth_headers)
    event_date = str(date.today() + timedelta(days=45))

    # First event succeeds
    await _create_event(
        async_client, auth_headers, venue_id=venue["id"], date=event_date
    )

    # Second event on the same date + venue should fail with 409
    resp = await async_client.post("/api/v1/events", headers=auth_headers, json={
        "title": "冲突婚礼",
        "date": event_date,
        "venue_id": venue["id"],
    })
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "CONFLICT_DETECTED"


async def test_staff_conflict_detection(async_client: AsyncClient, auth_headers, test_user):
    """
    The conflict-check endpoint detects staff scheduling conflicts.
    """
    event = await _create_event(async_client, auth_headers)
    event_date = str(date.today() + timedelta(days=30))

    # Add a staff schedule for the event
    from app.models.event import StaffSchedule, ScheduleStatus
    from tests.conftest import TestSessionLocal

    async with TestSessionLocal() as session:
        schedule = StaffSchedule(
            staff_id=test_user.id,
            event_id=event["id"],
            role="策划师",
            date=event_date,
            status=ScheduleStatus.assigned,
        )
        session.add(schedule)
        await session.commit()

    # Check for staff conflict
    resp = await async_client.get(
        "/api/v1/events/conflicts",
        headers=auth_headers,
        params={"date": event_date, "staff_ids": str(test_user.id)},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["has_conflicts"] is True


async def test_edit_event_excludes_self(async_client: AsyncClient, auth_headers):
    """
    Updating an event does not trigger a conflict with itself
    (exclude_event_id is used).
    """
    venue = await _create_venue(async_client, auth_headers)
    event_date = str(date.today() + timedelta(days=50))

    event = await _create_event(
        async_client, auth_headers, venue_id=venue["id"], date=event_date
    )

    # Update the same event (same date, same venue) -- should succeed
    resp = await async_client.put(
        f"/api/v1/events/{event['id']}",
        headers=auth_headers,
        json={"title": "更新后的婚礼"},
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "更新后的婚礼"


async def test_add_resource(async_client: AsyncClient, auth_headers):
    """POST /api/v1/events/{id}/resources adds a resource to an event."""
    event = await _create_event(async_client, auth_headers)

    resp = await async_client.post(
        f"/api/v1/events/{event['id']}/resources",
        headers=auth_headers,
        json={"resource_type": "equipment", "resource_id": 1, "quantity": 2},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["resource_type"] == "equipment"
    assert body["quantity"] == 2


async def test_remove_resource(async_client: AsyncClient, auth_headers):
    """DELETE /api/v1/events/{id}/resources/{rid} removes a resource."""
    event = await _create_event(async_client, auth_headers)

    add_resp = await async_client.post(
        f"/api/v1/events/{event['id']}/resources",
        headers=auth_headers,
        json={"resource_type": "vehicle", "resource_id": 5, "quantity": 1},
    )
    resource_id = add_resp.json()["id"]

    resp = await async_client.delete(
        f"/api/v1/events/{event['id']}/resources/{resource_id}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["message"] == "资源已移除"


async def test_staff_schedule_query(async_client: AsyncClient, auth_headers, test_user):
    """GET /api/v1/events/staff-schedule queries schedules."""
    event = await _create_event(async_client, auth_headers)
    event_date = str(date.today() + timedelta(days=30))

    from app.models.event import StaffSchedule, ScheduleStatus
    from tests.conftest import TestSessionLocal

    async with TestSessionLocal() as session:
        schedule = StaffSchedule(
            staff_id=test_user.id,
            event_id=event["id"],
            role="司仪",
            date=event_date,
            status=ScheduleStatus.confirmed,
        )
        session.add(schedule)
        await session.commit()

    resp = await async_client.get(
        "/api/v1/events/staff-schedule",
        headers=auth_headers,
        params={"staff_id": test_user.id},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) >= 1
    assert body[0]["staff_id"] == test_user.id


async def test_venue_availability(async_client: AsyncClient, auth_headers):
    """GET /api/v1/venues/{id}/availability returns booked dates."""
    venue = await _create_venue(async_client, auth_headers)
    event_date = date.today() + timedelta(days=60)

    # Create an event at the venue
    await _create_event(
        async_client, auth_headers,
        venue_id=venue["id"],
        date=str(event_date),
    )

    resp = await async_client.get(
        f"/api/v1/venues/{venue['id']}/availability",
        headers=auth_headers,
        params={
            "date_start": str(event_date),
            "date_end": str(event_date),
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["venue_id"] == venue["id"]
    assert str(event_date) in body["booked_dates"]
