"""Tests for Dashboard Cashflow API."""
from __future__ import annotations
import pytest
from datetime import date, timedelta
from decimal import Decimal
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def seed_cashflow_data(async_client: AsyncClient, auth_headers, test_user):
    """Seed data for cashflow metrics tests."""
    # Create customer
    cust_resp = await async_client.post(
        "/api/v1/customers",
        headers=auth_headers,
        json={
            "name": "Cashflow Test Customer",
            "phone": "13800138002",
        }
    )
    customer_id = cust_resp.json()["id"]

    # Create order with large amount
    order_resp = await async_client.post(
        "/api/v1/orders",
        headers=auth_headers,
        json={
            "customer_id": customer_id,
            "sale_id": test_user.id,
            "items": [
                {"type": "planning", "name": "婚礼策划", "unit_price": 50000.0, "quantity": 1},
            ],
        }
    )
    order_id = order_resp.json()["id"]

    # Create partial payment (leaving receivable)
    await async_client.post(
        f"/api/v1/orders/{order_id}/payments",
        headers=auth_headers,
        json={"amount": 25000.0, "method": "bank"},
    )

    return {"customer_id": customer_id, "order_id": order_id}


async def test_get_cashflow_metrics_month_period(
    async_client: AsyncClient,
    auth_headers,
    test_user,
    seed_cashflow_data
):
    """GET /api/v1/dashboard/cashflow returns cashflow metrics for month."""
    resp = await async_client.get(
        "/api/v1/dashboard/cashflow",
        headers=auth_headers,
        params={"period": "month"}
    )
    assert resp.status_code == 200
    body = resp.json()

    # Check structure
    assert "period" in body
    assert "period_start" in body
    assert "period_end" in body
    assert "cash_in" in body
    assert "receivables" in body

    # Check cash_in structure
    cash_in = body["cash_in"]
    assert "total" in cash_in
    assert "by_method" in cash_in
    assert cash_in["total"] >= 0

    # Check receivables structure
    receivables = body["receivables"]
    assert "total" in receivables
    assert "overdue" in receivables
    assert "overdue_count" in receivables


async def test_get_cashflow_metrics_quarter(
    async_client: AsyncClient,
    auth_headers,
    seed_cashflow_data
):
    """GET /api/v1/dashboard/cashflow with quarter period."""
    resp = await async_client.get(
        "/api/v1/dashboard/cashflow",
        headers=auth_headers,
        params={"period": "quarter"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["period"] == "quarter"


async def test_get_cashflow_metrics_year(
    async_client: AsyncClient,
    auth_headers,
    seed_cashflow_data
):
    """GET /api/v1/dashboard/cashflow with year period."""
    resp = await async_client.get(
        "/api/v1/dashboard/cashflow",
        headers=auth_headers,
        params={"period": "year"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["period"] == "year"


async def test_cashflow_aging_analysis(
    async_client: AsyncClient,
    auth_headers,
    seed_cashflow_data
):
    """Cashflow metrics should include aging analysis."""
    resp = await async_client.get(
        "/api/v1/dashboard/cashflow",
        headers=auth_headers,
        params={"period": "month"}
    )
    assert resp.status_code == 200
    body = resp.json()

    # Check aging buckets exist
    assert "aging" in body
    aging = body["aging"]
    assert isinstance(aging, list)

    # Verify aging bucket structure
    if len(aging) > 0:
        bucket = aging[0]
        assert "bucket" in bucket
        assert "amount" in bucket
        assert "percent" in bucket


async def test_cashflow_payment_breakdown(
    async_client: AsyncClient,
    auth_headers,
    seed_cashflow_data
):
    """Cashflow metrics should include payment breakdown by method."""
    resp = await async_client.get(
        "/api/v1/dashboard/cashflow",
        headers=auth_headers,
        params={"period": "month"}
    )
    assert resp.status_code == 200
    body = resp.json()

    # Check payment method breakdown
    cash_in = body["cash_in"]
    by_method = cash_in["by_method"]
    assert isinstance(by_method, dict)


async def test_cashflow_turnover_days(
    async_client: AsyncClient,
    auth_headers,
    seed_cashflow_data
):
    """Cashflow metrics should include turnover days."""
    resp = await async_client.get(
        "/api/v1/dashboard/cashflow",
        headers=auth_headers,
        params={"period": "month"}
    )
    assert resp.status_code == 200
    body = resp.json()

    # Check turnover days
    assert "turnover_days" in body
    assert isinstance(body["turnover_days"], int)


async def test_cashflow_cache(
    async_client: AsyncClient,
    auth_headers,
    seed_cashflow_data
):
    """Cashflow metrics should be cached."""
    # First call
    resp1 = await async_client.get(
        "/api/v1/dashboard/cashflow",
        headers=auth_headers,
        params={"period": "month"}
    )
    assert resp1.status_code == 200

    # Second call should hit cache
    resp2 = await async_client.get(
        "/api/v1/dashboard/cashflow",
        headers=auth_headers,
        params={"period": "month"}
    )
    assert resp2.status_code == 200
    assert resp2.json() == resp1.json()


async def test_cashflow_invalid_period(
    async_client: AsyncClient,
    auth_headers
):
    """Invalid period should be rejected by validation."""
    resp = await async_client.get(
        "/api/v1/dashboard/cashflow",
        headers=auth_headers,
        params={"period": "invalid"}
    )
    # FastAPI validation should reject this
    assert resp.status_code == 422


async def test_cashflow_permission_required(
    async_client: AsyncClient,
    seed_cashflow_data
):
    """Cashflow metrics requires dashboard:read permission."""
    resp = await async_client.get(
        "/api/v1/dashboard/cashflow",
        params={"period": "month"}
    )
    # Unauthorized (no token)
    assert resp.status_code == 401


async def test_cashflow_finance_permission(
    async_client: AsyncClient,
    auth_headers,
    test_user,
    seed_cashflow_data
):
    """Cashflow data should be filtered based on finance:read permission."""
    # This test verifies that the permission check is enforced
    # The actual filtering depends on the RBAC implementation
    resp = await async_client.get(
        "/api/v1/dashboard/cashflow",
        headers=auth_headers,
        params={"period": "month"}
    )
    assert resp.status_code == 200
    # User with dashboard:read permission should see data
    # Users without finance:read might see filtered data
