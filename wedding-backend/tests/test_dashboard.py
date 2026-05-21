from __future__ import annotations
"""
Tests for dashboard endpoints: /api/v1/dashboard/*
"""

import pytest
from datetime import date, timedelta
from httpx import AsyncClient
import uuid


pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _seed_data(client: AsyncClient, headers: dict, sale_id: int):
    """Create minimal data (customer, order, supplier, event) for dashboard."""
    # Customer
    cust_resp = await client.post("/api/v1/customers", headers=headers, json={
        "name": "仪表盘客户-" + uuid.uuid4().hex[:6],
        "phone": "4" + uuid.uuid4().hex[:10],
    })
    customer_id = cust_resp.json()["id"]

    # Order
    order_resp = await client.post("/api/v1/orders", headers=headers, json={
        "customer_id": customer_id,
        "sale_id": sale_id,
        "items": [{"type": "planning", "name": "婚礼策划", "unit_price": 12000.0}],
    })
    order_id = order_resp.json()["id"]

    # Payment
    await client.post(
        f"/api/v1/orders/{order_id}/payments", headers=headers,
        json={"amount": 6000.0, "method": "wechat"},
    )

    # Supplier
    sup_resp = await client.post("/api/v1/suppliers", headers=headers, json={
        "name": "仪表盘供应商-" + uuid.uuid4().hex[:6],
        "type": "floral",
    })
    supplier_id = sup_resp.json()["id"]

    # Supplier evaluation
    await client.post(
        f"/api/v1/suppliers/{supplier_id}/evaluations", headers=headers,
        json={"order_id": order_id, "rating": 5},
    )

    # Venue + Event
    venue_resp = await client.post("/api/v1/venues", headers=headers, json={
        "name": "仪表盘场地-" + uuid.uuid4().hex[:6],
        "address": "某路1号",
        "capacity": 300,
        "price": 20000.0,
    })
    venue_id = venue_resp.json()["id"]

    event_date = str(date.today() + timedelta(days=15))
    await client.post("/api/v1/events", headers=headers, json={
        "title": "仪表盘活动",
        "date": event_date,
        "venue_id": venue_id,
    })

    return {"customer_id": customer_id, "order_id": order_id, "supplier_id": supplier_id}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

async def test_overview(async_client: AsyncClient, auth_headers, test_user):
    """GET /api/v1/dashboard/overview returns aggregated stats."""
    await _seed_data(async_client, auth_headers, test_user.id)

    resp = await async_client.get("/api/v1/dashboard/overview", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "customers" in body
    assert "orders" in body
    assert "upcoming_events" in body
    assert body["orders"]["count"] >= 1


async def test_sales_ranking(async_client: AsyncClient, auth_headers, test_user):
    """GET /api/v1/dashboard/sales-ranking returns ranked salespeople."""
    await _seed_data(async_client, auth_headers, test_user.id)

    resp = await async_client.get(
        "/api/v1/dashboard/sales-ranking", headers=auth_headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "ranking" in body
    assert len(body["ranking"]) >= 1
    assert body["ranking"][0]["sale_name"] == test_user.name


async def test_conversion_funnel(async_client: AsyncClient, auth_headers, test_user):
    """GET /api/v1/dashboard/conversion-funnel returns funnel data."""
    await _seed_data(async_client, auth_headers, test_user.id)

    resp = await async_client.get(
        "/api/v1/dashboard/conversion-funnel", headers=auth_headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "funnel" in body
    statuses = [step["status"] for step in body["funnel"]]
    assert "potential" in statuses


async def test_finance_summary(async_client: AsyncClient, auth_headers, test_user):
    """GET /api/v1/dashboard/finance-summary returns financial data."""
    await _seed_data(async_client, auth_headers, test_user.id)

    resp = await async_client.get(
        "/api/v1/dashboard/finance-summary", headers=auth_headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["order_count"] >= 1
    assert float(body["total_paid"]) >= 0
    assert "payment_method_breakdown" in body


async def test_schedule_heatmap(async_client: AsyncClient, auth_headers, test_user):
    """GET /api/v1/dashboard/schedule-heatmap returns date-based event counts."""
    await _seed_data(async_client, auth_headers, test_user.id)

    month = (date.today() + timedelta(days=15)).strftime("%Y-%m")
    resp = await async_client.get(
        "/api/v1/dashboard/schedule-heatmap",
        headers=auth_headers,
        params={"month": month},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["month"] == month
    assert isinstance(body["heatmap"], list)


async def test_supplier_ranking(async_client: AsyncClient, auth_headers, test_user):
    """GET /api/v1/dashboard/supplier-ranking returns ranked suppliers."""
    await _seed_data(async_client, auth_headers, test_user.id)

    resp = await async_client.get(
        "/api/v1/dashboard/supplier-ranking", headers=auth_headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "ranking" in body
    assert len(body["ranking"]) >= 1
