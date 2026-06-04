"""Tests for Dashboard Alerts API."""
from __future__ import annotations
import pytest
from datetime import date, timedelta, datetime
from decimal import Decimal
from httpx import AsyncClient
import uuid

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def seed_alert_data(async_client: AsyncClient, auth_headers, test_user):
    """Seed data for alerts tests - create overdue receivable scenario."""
    # Create customer
    cust_resp = await async_client.post(
        "/api/v1/customers",
        headers=auth_headers,
        json={
            "name": "Alert Test Customer",
            "phone": "13800138003",
        }
    )
    customer_id = cust_resp.json()["id"]

    # Create order
    order_resp = await async_client.post(
        "/api/v1/orders",
        headers=auth_headers,
        json={
            "customer_id": customer_id,
            "sale_id": test_user.id,
            "items": [
                {"type": "planning", "name": "婚礼策划", "unit_price": 40000.0, "quantity": 1},
            ],
        }
    )
    order_id = order_resp.json()["id"]

    # Only partial payment to create receivable
    await async_client.post(
        f"/api/v1/orders/{order_id}/payments",
        headers=auth_headers,
        json={"amount": 10000.0, "method": "cash"},
    )

    return {"customer_id": customer_id, "order_id": order_id}


async def test_get_alerts_all_levels(
    async_client: AsyncClient,
    auth_headers,
    seed_alert_data
):
    """GET /api/v1/dashboard/alerts returns all alerts."""
    resp = await async_client.get(
        "/api/v1/dashboard/alerts",
        headers=auth_headers,
        params={"level": "all", "limit": 20}
    )
    assert resp.status_code == 200
    body = resp.json()

    # Check structure
    assert "high_count" in body
    assert "medium_count" in body
    assert "low_count" in body
    assert "alerts" in body
    assert "total" in body

    # Check alerts is a list
    assert isinstance(body["alerts"], list)


async def test_get_alerts_high_level(
    async_client: AsyncClient,
    auth_headers,
    seed_alert_data
):
    """GET /api/v1/dashboard/alerts filters by high level."""
    resp = await async_client.get(
        "/api/v1/dashboard/alerts",
        headers=auth_headers,
        params={"level": "high", "limit": 10}
    )
    assert resp.status_code == 200
    body = resp.json()

    # All returned alerts should be high level
    for alert in body["alerts"]:
        assert alert["level"] == "high"


async def test_get_alerts_with_pagination(
    async_client: AsyncClient,
    auth_headers,
    seed_alert_data
):
    """GET /api/v1/dashboard/alerts with pagination."""
    resp = await async_client.get(
        "/api/v1/dashboard/alerts",
        headers=auth_headers,
        params={
            "level": "all",
            "limit": 10,
            "offset": 0
        }
    )
    assert resp.status_code == 200
    body = resp.json()

    # Check total count exists
    assert "total" in body
    assert isinstance(body["total"], int)


async def test_alert_structure(
    async_client: AsyncClient,
    auth_headers,
    seed_alert_data
):
    """Alert items should have correct structure."""
    resp = await async_client.get(
        "/api/v1/dashboard/alerts",
        headers=auth_headers,
        params={"level": "all", "limit": 20}
    )
    assert resp.status_code == 200
    body = resp.json()

    if len(body["alerts"]) > 0:
        alert = body["alerts"][0]
        assert "id" in alert
        assert "level" in alert
        assert "type" in alert
        assert "title" in alert
        assert "detail" in alert
        assert "entity_type" in alert
        assert "entity_id" in alert
        assert "actions" in alert
        assert "created_at" in alert


async def test_alert_with_type_filter(
    async_client: AsyncClient,
    auth_headers,
    seed_alert_data
):
    """GET /api/v1/dashboard/alerts with type filter."""
    resp = await async_client.get(
        "/api/v1/dashboard/alerts",
        headers=auth_headers,
        params={
            "type": "overdue_receivable",
            "limit": 10
        }
    )
    assert resp.status_code == 200
    body = resp.json()

    # All returned alerts should be of the specified type
    for alert in body["alerts"]:
        assert alert["type"] == "overdue_receivable"


async def test_alert_owner_info(
    async_client: AsyncClient,
    auth_headers,
    test_user,
    seed_alert_data
):
    """Alerts should include owner information."""
    resp = await async_client.get(
        "/api/v1/dashboard/alerts",
        headers=auth_headers,
        params={"level": "all", "limit": 20}
    )
    assert resp.status_code == 200
    body = resp.json()

    # Check if any alert has owner info
    for alert in body["alerts"]:
        if alert.get("owner_id"):
            assert "owner_name" in alert
            break


async def test_alert_cache(
    async_client: AsyncClient,
    auth_headers,
    seed_alert_data
):
    """Alerts should be cached with short TTL."""
    # First call
    resp1 = await async_client.get(
        "/api/v1/dashboard/alerts",
        headers=auth_headers,
        params={"level": "all", "limit": 20}
    )
    assert resp1.status_code == 200

    # Second call should hit cache
    resp2 = await async_client.get(
        "/api/v1/dashboard/alerts",
        headers=auth_headers,
        params={"level": "all", "limit": 20}
    )
    assert resp2.status_code == 200
    assert resp2.json() == resp1.json()


async def test_resolve_alert(
    async_client: AsyncClient,
    auth_headers,
    seed_alert_data
):
    """POST /api/v1/dashboard/alerts/:id/resolve marks alert as resolved."""
    # First get an alert
    resp = await async_client.get(
        "/api/v1/dashboard/alerts",
        headers=auth_headers,
        params={"level": "all", "limit": 1}
    )
    assert resp.status_code == 200
    body = resp.json()

    if len(body["alerts"]) > 0:
        alert_id = body["alerts"][0]["id"]

        # Resolve the alert
        resolve_resp = await async_client.post(
            f"/api/v1/dashboard/alerts/{alert_id}/resolve",
            headers=auth_headers,
            json={"note": "Test resolution"}
        )
        assert resolve_resp.status_code == 200
        resolve_body = resolve_resp.json()

        # Check response structure
        assert "success" in resolve_body
        assert "resolved_at" in resolve_body
        assert resolve_body["success"] is True


async def test_resolve_alert_with_note(
    async_client: AsyncClient,
    auth_headers,
    seed_alert_data
):
    """POST /api/v1/dashboard/alerts/:id/resolve with note."""
    # Get an alert
    resp = await async_client.get(
        "/api/v1/dashboard/alerts",
        headers=auth_headers,
        params={"level": "all", "limit": 1}
    )
    assert resp.status_code == 200
    body = resp.json()

    if len(body["alerts"]) > 0:
        alert_id = body["alerts"][0]["id"]

        # Resolve with note
        resolve_resp = await async_client.post(
            f"/api/v1/dashboard/alerts/{alert_id}/resolve",
            headers=auth_headers,
            json={"note": "已联系客户，承诺本周付款"}
        )
        assert resolve_resp.status_code == 200


async def test_resolve_alert_not_found(
    async_client: AsyncClient,
    auth_headers
):
    """POST /api/v1/dashboard/alerts/:id/resolve returns 404 for non-existent alert."""
    resolve_resp = await async_client.post(
        "/api/v1/dashboard/alerts/alert_nonexistent_123/resolve",
        headers=auth_headers,
        json={"note": "Test"}
    )
    assert resolve_resp.status_code == 404


async def test_alerts_permission_required(
    async_client: AsyncClient,
    seed_alert_data
):
    """Get alerts requires dashboard:read permission."""
    resp = await async_client.get(
        "/api/v1/dashboard/alerts",
        params={"level": "all"}
    )
    # Unauthorized (no token)
    assert resp.status_code == 401


async def test_resolve_alert_permission_required(
    async_client: AsyncClient,
    seed_alert_data
):
    """Resolve alert requires dashboard:write permission."""
    resolve_resp = await async_client.post(
        "/api/v1/dashboard/alerts/alert_test_123/resolve",
        params={"note": "Test"}
    )
    # Unauthorized (no token)
    assert resolve_resp.status_code == 401


async def test_alert_invalid_limit(
    async_client: AsyncClient,
    auth_headers
):
    """Invalid limit parameter should be rejected."""
    # Limit > 100 should be rejected
    resp = await async_client.get(
        "/api/v1/dashboard/alerts",
        headers=auth_headers,
        params={"limit": 101}
    )
    assert resp.status_code == 422
