"""Tests for Dashboard Team Efficiency API."""
from __future__ import annotations
import pytest
from datetime import date, timedelta
from decimal import Decimal
from httpx import AsyncClient
import uuid

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def seed_team_data(async_client: AsyncClient, auth_headers, test_user):
    """Seed data for team efficiency tests."""
    customers = []
    orders = []

    # Create multiple customers and orders
    for i in range(3):
        # Customer
        cust_resp = await async_client.post(
            "/api/v1/customers",
            headers=auth_headers,
            json={
                "name": f"Team Test Customer {i}",
                "phone": f"13800138{i:02d}",
                "source": "xiaohongshu" if i % 2 == 0 else "referral",
            }
        )
        customer_id = cust_resp.json()["id"]
        customers.append(customer_id)

        # Order
        order_resp = await async_client.post(
            "/api/v1/orders",
            headers=auth_headers,
            json={
                "customer_id": customer_id,
                "sale_id": test_user.id,
                "items": [
                    {"type": "planning", "name": "婚礼策划", "unit_price": 30000.0 + i * 5000, "quantity": 1},
                ],
            }
        )
        order_id = order_resp.json()["id"]
        orders.append(order_id)

        # Payment for first order
        if i == 0:
            await async_client.post(
                f"/api/v1/orders/{order_id}/payments",
                headers=auth_headers,
                json={"amount": 15000.0, "method": "wechat"},
            )

    return {"customers": customers, "orders": orders}


async def test_get_team_efficiency_month_period(
    async_client: AsyncClient,
    auth_headers,
    test_user,
    seed_team_data
):
    """GET /api/v1/dashboard/team-efficiency returns team metrics for month."""
    resp = await async_client.get(
        "/api/v1/dashboard/team-efficiency",
        headers=auth_headers,
        params={"period": "month"}
    )
    assert resp.status_code == 200
    body = resp.json()

    # Check structure
    assert "period" in body
    assert "period_start" in body
    assert "period_end" in body
    assert "teams" in body
    assert "funnel" in body
    assert "ranking" in body


async def test_get_team_efficiency_with_pagination(
    async_client: AsyncClient,
    auth_headers,
    test_user,
    seed_team_data
):
    """GET /api/v1/dashboard/team-efficiency with pagination."""
    resp = await async_client.get(
        "/api/v1/dashboard/team-efficiency",
        headers=auth_headers,
        params={
            "period": "month",
            "page": 1,
            "page_size": 10
        }
    )
    assert resp.status_code == 200
    body = resp.json()

    # Check pagination structure
    assert "total" in body
    assert "page" in body
    assert "page_size" in body
    assert body["page"] == 1
    assert body["page_size"] == 10


async def test_team_efficiency_teams_breakdown(
    async_client: AsyncClient,
    auth_headers,
    test_user,
    seed_team_data
):
    """Team efficiency should include teams breakdown."""
    resp = await async_client.get(
        "/api/v1/dashboard/team-efficiency",
        headers=auth_headers,
        params={"period": "month"}
    )
    assert resp.status_code == 200
    body = resp.json()

    # Check teams structure
    teams = body["teams"]
    assert isinstance(teams, list)

    if len(teams) > 0:
        team = teams[0]
        assert "team" in team
        assert "total_revenue" in team
        assert "headcount" in team
        assert "avg_revenue" in team


async def test_team_efficiency_funnel(
    async_client: AsyncClient,
    auth_headers,
    seed_team_data
):
    """Team efficiency should include conversion funnel."""
    resp = await async_client.get(
        "/api/v1/dashboard/team-efficiency",
        headers=auth_headers,
        params={"period": "month"}
    )
    assert resp.status_code == 200
    body = resp.json()

    # Check funnel structure
    funnel = body["funnel"]
    assert isinstance(funnel, list)

    # Verify funnel stages
    if len(funnel) > 0:
        stage = funnel[0]
        assert "stage" in stage
        assert "count" in stage
        assert "rate" in stage


async def test_team_efficiency_ranking(
    async_client: AsyncClient,
    auth_headers,
    test_user,
    seed_team_data
):
    """Team efficiency should include sales ranking."""
    resp = await async_client.get(
        "/api/v1/dashboard/team-efficiency",
        headers=auth_headers,
        params={"period": "month"}
    )
    assert resp.status_code == 200
    body = resp.json()

    # Check ranking structure
    ranking = body["ranking"]
    assert isinstance(ranking, list)

    if len(ranking) > 0:
        sales = ranking[0]
        assert "rank" in sales
        assert "sale_id" in sales
        assert "sale_name" in sales
        assert "order_count" in sales
        assert "revenue" in sales
        assert "avg_order_value" in sales
        assert "conversion_rate" in sales


async def test_team_efficiency_new_customers(
    async_client: AsyncClient,
    auth_headers,
    seed_team_data
):
    """Team efficiency should include new customers count."""
    resp = await async_client.get(
        "/api/v1/dashboard/team-efficiency",
        headers=auth_headers,
        params={"period": "month"}
    )
    assert resp.status_code == 200
    body = resp.json()

    # Check new customers count
    assert "new_customers" in body
    assert isinstance(body["new_customers"], int)


async def test_team_efficiency_follow_up_count(
    async_client: AsyncClient,
    auth_headers,
    seed_team_data
):
    """Team efficiency should include follow-up count."""
    resp = await async_client.get(
        "/api/v1/dashboard/team-efficiency",
        headers=auth_headers,
        params={"period": "month"}
    )
    assert resp.status_code == 200
    body = resp.json()

    # Check follow-up count
    assert "follow_up_count" in body
    assert isinstance(body["follow_up_count"], int)


async def test_team_efficiency_quarter_period(
    async_client: AsyncClient,
    auth_headers,
    seed_team_data
):
    """GET /api/v1/dashboard/team-efficiency with quarter period."""
    resp = await async_client.get(
        "/api/v1/dashboard/team-efficiency",
        headers=auth_headers,
        params={"period": "quarter"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["period"] == "quarter"


async def test_team_efficiency_year_period(
    async_client: AsyncClient,
    auth_headers,
    seed_team_data
):
    """GET /api/v1/dashboard/team-efficiency with year period."""
    resp = await async_client.get(
        "/api/v1/dashboard/team-efficiency",
        headers=auth_headers,
        params={"period": "year"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["period"] == "year"


async def test_team_efficiency_with_team_filter(
    async_client: AsyncClient,
    auth_headers,
    seed_team_data
):
    """GET /api/v1/dashboard/team-efficiency with team filter."""
    resp = await async_client.get(
        "/api/v1/dashboard/team-efficiency",
        headers=auth_headers,
        params={
            "period": "month",
            "team": "sales"
        }
    )
    assert resp.status_code == 200
    # Should return filtered data


async def test_team_efficiency_cache(
    async_client: AsyncClient,
    auth_headers,
    seed_team_data
):
    """Team efficiency metrics should be cached."""
    # First call
    resp1 = await async_client.get(
        "/api/v1/dashboard/team-efficiency",
        headers=auth_headers,
        params={"period": "month"}
    )
    assert resp1.status_code == 200

    # Second call should hit cache
    resp2 = await async_client.get(
        "/api/v1/dashboard/team-efficiency",
        headers=auth_headers,
        params={"period": "month"}
    )
    assert resp2.status_code == 200
    assert resp2.json() == resp1.json()


async def test_team_efficiency_invalid_period(
    async_client: AsyncClient,
    auth_headers
):
    """Invalid period should be rejected by validation."""
    resp = await async_client.get(
        "/api/v1/dashboard/team-efficiency",
        headers=auth_headers,
        params={"period": "invalid"}
    )
    # FastAPI validation should reject this
    assert resp.status_code == 422


async def test_team_efficiency_permission_required(
    async_client: AsyncClient,
    seed_team_data
):
    """Team efficiency requires dashboard:read permission."""
    resp = await async_client.get(
        "/api/v1/dashboard/team-efficiency",
        params={"period": "month"}
    )
    # Unauthorized (no token)
    assert resp.status_code == 401
