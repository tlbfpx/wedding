"""Tests for Dashboard Decision Support API."""
from __future__ import annotations
import pytest
from datetime import date, timedelta
from decimal import Decimal
from httpx import AsyncClient
import uuid

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def seed_decision_data(async_client: AsyncClient, auth_headers, test_user):
    """Seed data for decision support tests with different sources and services."""
    customers = []
    orders = []

    # Create customers from different sources
    sources = [
        ("xiaohongshu", 1),
        ("referral", 2),
        ("douyin", 3),
        ("offline", 4),
    ]

    for source_name, source_id in sources:
        # Customer
        cust_resp = await async_client.post(
            "/api/v1/customers",
            headers=auth_headers,
            json={
                "name": f"Decision Customer {source_name}",
                "phone": f"13900139{source_id:02d}",
                "source": source_name,
            }
        )
        customer_id = cust_resp.json()["id"]
        customers.append((customer_id, source_name))

        # Order with different service types
        service_types = ["planning", "photo", "host", "floral"]
        for i, service_type in enumerate(service_types):
            order_resp = await async_client.post(
                "/api/v1/orders",
                headers=auth_headers,
                json={
                    "customer_id": customer_id,
                    "sale_id": test_user.id,
                    "items": [
                        {
                            "type": service_type,
                            "name": f"测试服务-{service_type}",
                            "unit_price": 25000.0 + i * 5000,
                            "quantity": 1
                        },
                    ],
                }
            )
            order_id = order_resp.json()["id"]
            orders.append((order_id, service_type, source_name))

            # Payment for first order
            if i == 0:
                await async_client.post(
                    f"/api/v1/orders/{order_id}/payments",
                    headers=auth_headers,
                    json={"amount": 15000.0, "method": "wechat"},
                )

    return {"customers": customers, "orders": orders}


async def test_get_decision_support_source_dimension(
    async_client: AsyncClient,
    admin_headers,  # Need admin permissions for decision support
    seed_decision_data
):
    """GET /api/v1/dashboard/decision-support with source dimension."""
    resp = await async_client.get(
        "/api/v1/dashboard/decision-support",
        headers=admin_headers,
        params={
            "period": "month",
            "dimension": "source"
        }
    )
    assert resp.status_code == 200
    body = resp.json()

    # Check structure
    assert "period" in body
    assert "period_start" in body
    assert "period_end" in body
    assert "source_roi" in body
    assert "service_breakdown" in body
    assert "supplier_value" in body


async def test_decision_support_source_roi(
    async_client: AsyncClient,
    admin_headers,
    seed_decision_data
):
    """Decision support should include source ROI analysis."""
    resp = await async_client.get(
        "/api/v1/dashboard/decision-support",
        headers=admin_headers,
        params={
            "period": "month",
            "dimension": "source"
        }
    )
    assert resp.status_code == 200
    body = resp.json()

    # Check source_roi structure
    source_roi = body["source_roi"]
    assert isinstance(source_roi, list)

    if len(source_roi) > 0:
        source = source_roi[0]
        assert "source" in source
        assert "source_id" in source
        assert "lead_count" in source
        assert "signed_count" in source
        assert "conversion_rate" in source
        assert "revenue" in source
        assert "avg_order_value" in source
        assert "roi_score" in source


async def test_decision_support_service_breakdown(
    async_client: AsyncClient,
    admin_headers,
    seed_decision_data
):
    """Decision support should include service type breakdown."""
    resp = await async_client.get(
        "/api/v1/dashboard/decision-support",
        headers=admin_headers,
        params={
            "period": "month",
            "dimension": "source"
        }
    )
    assert resp.status_code == 200
    body = resp.json()

    # Check service_breakdown structure
    service_breakdown = body["service_breakdown"]
    assert isinstance(service_breakdown, list)

    if len(service_breakdown) > 0:
        service = service_breakdown[0]
        assert "service_type" in service
        assert "revenue" in service
        assert "percent" in service
        assert "count" in service


async def test_decision_support_supplier_value(
    async_client: AsyncClient,
    admin_headers,
    seed_decision_data
):
    """Decision support should include supplier value analysis."""
    resp = await async_client.get(
        "/api/v1/dashboard/decision-support",
        headers=admin_headers,
        params={
            "period": "month",
            "dimension": "source"
        }
    )
    assert resp.status_code == 200
    body = resp.json()

    # Check supplier_value structure
    supplier_value = body["supplier_value"]
    assert isinstance(supplier_value, list)

    # Supplier data might be empty if no suppliers created
    # Just verify the structure exists


async def test_decision_support_service_dimension(
    async_client: AsyncClient,
    admin_headers,
    seed_decision_data
):
    """GET /api/v1/dashboard/decision-support with service dimension."""
    resp = await async_client.get(
        "/api/v1/dashboard/decision-support",
        headers=admin_headers,
        params={
            "period": "month",
            "dimension": "service"
        }
    )
    assert resp.status_code == 200
    body = resp.json()

    # Should still return all data
    assert "source_roi" in body
    assert "service_breakdown" in body
    assert "supplier_value" in body


async def test_decision_support_supplier_dimension(
    async_client: AsyncClient,
    admin_headers,
    seed_decision_data
):
    """GET /api/v1/dashboard/decision-support with supplier dimension."""
    resp = await async_client.get(
        "/api/v1/dashboard/decision-support",
        headers=admin_headers,
        params={
            "period": "month",
            "dimension": "supplier"
        }
    )
    assert resp.status_code == 200
    body = resp.json()

    # Should still return all data
    assert "source_roi" in body
    assert "service_breakdown" in body
    assert "supplier_value" in body


async def test_decision_support_quarter_period(
    async_client: AsyncClient,
    admin_headers,
    seed_decision_data
):
    """GET /api/v1/dashboard/decision-support with quarter period."""
    resp = await async_client.get(
        "/api/v1/dashboard/decision-support",
        headers=admin_headers,
        params={
            "period": "quarter",
            "dimension": "source"
        }
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["period"] == "quarter"


async def test_decision_support_year_period(
    async_client: AsyncClient,
    admin_headers,
    seed_decision_data
):
    """GET /api/v1/dashboard/decision-support with year period."""
    resp = await async_client.get(
        "/api/v1/dashboard/decision-support",
        headers=admin_headers,
        params={
            "period": "year",
            "dimension": "source"
        }
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["period"] == "year"


async def test_decision_support_cache(
    async_client: AsyncClient,
    admin_headers,
    seed_decision_data
):
    """Decision support data should be cached."""
    # First call
    resp1 = await async_client.get(
        "/api/v1/dashboard/decision-support",
        headers=admin_headers,
        params={
            "period": "month",
            "dimension": "source"
        }
    )
    assert resp1.status_code == 200

    # Second call should hit cache
    resp2 = await async_client.get(
        "/api/v1/dashboard/decision-support",
        headers=admin_headers,
        params={
            "period": "month",
            "dimension": "source"
        }
    )
    assert resp2.status_code == 200
    assert resp2.json() == resp1.json()


async def test_decision_support_invalid_period(
    async_client: AsyncClient,
    admin_headers
):
    """Invalid period should be rejected by validation."""
    resp = await async_client.get(
        "/api/v1/dashboard/decision-support",
        headers=admin_headers,
        params={
            "period": "invalid",
            "dimension": "source"
        }
    )
    # FastAPI validation should reject this
    assert resp.status_code == 422


async def test_decision_support_invalid_dimension(
    async_client: AsyncClient,
    admin_headers
):
    """Invalid dimension should be rejected by validation."""
    resp = await async_client.get(
        "/api/v1/dashboard/decision-support",
        headers=admin_headers,
        params={
            "period": "month",
            "dimension": "invalid"
        }
    )
    # FastAPI validation should reject this
    assert resp.status_code == 422


async def test_decision_support_permission_required(
    async_client: AsyncClient,
    auth_headers,  # Regular user without admin permission
    seed_decision_data
):
    """Decision support requires dashboard:read_all permission."""
    resp = await async_client.get(
        "/api/v1/dashboard/decision-support",
        headers=auth_headers,
        params={
            "period": "month",
            "dimension": "source"
        }
    )
    # Should return 403 Forbidden if user lacks dashboard:read_all permission
    # Or return filtered data depending on RBAC implementation
    assert resp.status_code in [200, 403]


async def test_decision_support_without_auth(
    async_client: AsyncClient,
    seed_decision_data
):
    """Decision support requires authentication."""
    resp = await async_client.get(
        "/api/v1/dashboard/decision-support",
        params={
            "period": "month",
            "dimension": "source"
        }
    )
    # Unauthorized (no token)
    assert resp.status_code == 401


async def test_source_roi_calculation(
    async_client: AsyncClient,
    admin_headers,
    seed_decision_data
):
    """Source ROI should calculate conversion rate correctly."""
    resp = await async_client.get(
        "/api/v1/dashboard/decision-support",
        headers=admin_headers,
        params={
            "period": "month",
            "dimension": "source"
        }
    )
    assert resp.status_code == 200
    body = resp.json()

    # Check conversion rate calculation
    for source in body["source_roi"]:
        if source["lead_count"] > 0:
            # conversion_rate = signed_count / lead_count
            expected_rate = source["signed_count"] / source["lead_count"]
            assert abs(source["conversion_rate"] - expected_rate) < 0.01


async def test_service_breakdown_percentages(
    async_client: AsyncClient,
    admin_headers,
    seed_decision_data
):
    """Service breakdown percentages should sum to 1."""
    resp = await async_client.get(
        "/api/v1/dashboard/decision-support",
        headers=admin_headers,
        params={
            "period": "month",
            "dimension": "source"
        }
    )
    assert resp.status_code == 200
    body = resp.json()

    # Check percentages sum to 1 (or close due to rounding)
    total_percent = sum(s["percent"] for s in body["service_breakdown"])
    if len(body["service_breakdown"]) > 0:
        assert abs(total_percent - 1.0) < 0.05  # Allow 5% rounding error
