"""Tests for Dashboard Health Metrics API."""
from __future__ import annotations
import pytest
from datetime import date, timedelta
from decimal import Decimal
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def seed_health_data(async_client: AsyncClient, auth_headers, test_user):
    """Seed data for health metrics tests."""
    # Create customer
    cust_resp = await async_client.post(
        "/api/v1/customers",
        headers=auth_headers,
        json={
            "name": "Health Test Customer",
            "phone": "13800138001",
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
                {"type": "planning", "name": "婚礼策划", "unit_price": 30000.0, "quantity": 1},
            ],
        }
    )
    order_id = order_resp.json()["id"]

    # Create payment
    await async_client.post(
        f"/api/v1/orders/{order_id}/payments",
        headers=auth_headers,
        json={"amount": 15000.0, "method": "wechat"},
    )

    return {"customer_id": customer_id, "order_id": order_id}


async def test_get_health_metrics_month_period(
    async_client: AsyncClient,
    auth_headers,
    test_user,
    seed_health_data
):
    """GET /api/v1/dashboard/health returns health metrics for month."""
    resp = await async_client.get(
        "/api/v1/dashboard/health",
        headers=auth_headers,
        params={"period": "month"}
    )
    assert resp.status_code == 200
    body = resp.json()

    # Check structure
    assert "period" in body
    assert "period_start" in body
    assert "period_end" in body
    assert "metrics" in body

    # Check metrics exist
    metrics = body["metrics"]
    assert "revenue" in metrics
    assert "orders" in metrics
    assert "avg_order_value" in metrics
    assert "sign_rate" in metrics

    # Check metric structure
    assert "value" in metrics["revenue"]
    assert metrics["revenue"]["value"] >= 0
    assert metrics["orders"]["value"] >= 1


async def test_get_health_metrics_with_compare(
    async_client: AsyncClient,
    auth_headers,
    test_user,
    seed_health_data
):
    """GET /api/v1/dashboard/health with compare_to parameter."""
    resp = await async_client.get(
        "/api/v1/dashboard/health",
        headers=auth_headers,
        params={
            "period": "month",
            "compare_to": "prev_period"
        }
    )
    assert resp.status_code == 200
    body = resp.json()

    # Should have comparison period dates
    assert "compare_period_start" in body
    assert "compare_period_end" in body

    # Metrics should have trend
    assert "trend" in body["metrics"]["revenue"]


async def test_get_health_metrics_quarter(
    async_client: AsyncClient,
    auth_headers,
    seed_health_data
):
    """GET /api/v1/dashboard/health with quarter period."""
    resp = await async_client.get(
        "/api/v1/dashboard/health",
        headers=auth_headers,
        params={"period": "quarter"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["period"] == "quarter"


async def test_get_health_metrics_year(
    async_client: AsyncClient,
    auth_headers,
    seed_health_data
):
    """GET /api/v1/dashboard/health with year period."""
    resp = await async_client.get(
        "/api/v1/dashboard/health",
        headers=auth_headers,
        params={"period": "year"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["period"] == "year"


async def test_health_metrics_cache(
    async_client: AsyncClient,
    auth_headers,
    seed_health_data
):
    """Health metrics should be cached."""
    # First call
    resp1 = await async_client.get(
        "/api/v1/dashboard/health",
        headers=auth_headers,
        params={"period": "month"}
    )
    assert resp1.status_code == 200

    # Second call should hit cache
    resp2 = await async_client.get(
        "/api/v1/dashboard/health",
        headers=auth_headers,
        params={"period": "month"}
    )
    assert resp2.status_code == 200
    assert resp2.json() == resp1.json()


async def test_health_metrics_invalid_period(
    async_client: AsyncClient,
    auth_headers
):
    """Invalid period should be rejected by validation."""
    resp = await async_client.get(
        "/api/v1/dashboard/health",
        headers=auth_headers,
        params={"period": "invalid"}
    )
    # FastAPI validation should reject this
    assert resp.status_code == 422


async def test_health_metrics_permission_required(
    async_client: AsyncClient,
    seed_health_data
):
    """Health metrics requires dashboard:read permission."""
    resp = await async_client.get(
        "/api/v1/dashboard/health",
        params={"period": "month"}
    )
    # Unauthorized (no token)
    assert resp.status_code == 401
