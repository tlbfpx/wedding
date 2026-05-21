from __future__ import annotations
"""
Tests for supplier endpoints: /api/v1/suppliers/*
"""

import pytest
from httpx import AsyncClient


pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _create_supplier(client: AsyncClient, headers: dict, **overrides) -> dict:
    payload = {
        "name": "测试供应商",
        "type": "floral",
        "contact": "李花艺",
        "phone": "13700001111",
        "address": "花艺市场A区",
    }
    payload.update(overrides)
    resp = await client.post("/api/v1/suppliers", headers=headers, json=payload)
    assert resp.status_code == 200
    return resp.json()


async def _create_order(client: AsyncClient, headers: dict, customer_id: int, sale_id: int) -> dict:
    resp = await client.post("/api/v1/orders", headers=headers, json={
        "customer_id": customer_id,
        "sale_id": sale_id,
        "items": [{"type": "floral", "name": "花艺布置", "unit_price": 5000.0}],
    })
    assert resp.status_code == 200
    return resp.json()


async def _create_customer(client: AsyncClient, headers: dict) -> dict:
    import uuid
    resp = await client.post("/api/v1/customers", headers=headers, json={
        "name": "客户-" + uuid.uuid4().hex[:6],
        "phone": "1" + uuid.uuid4().hex[:10],
    })
    assert resp.status_code == 200
    return resp.json()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

async def test_create_supplier(async_client: AsyncClient, auth_headers):
    """POST /api/v1/suppliers creates a new supplier."""
    body = await _create_supplier(async_client, auth_headers, name="花好月圆花艺")
    assert body["name"] == "花好月圆花艺"
    assert body["type"] == "floral"
    assert body["cooperation_status"] == "active"
    assert body["rating"] == 0.0


async def test_list_suppliers(async_client: AsyncClient, auth_headers):
    """GET /api/v1/suppliers returns paginated supplier list."""
    await _create_supplier(async_client, auth_headers, name="供应商A")
    await _create_supplier(async_client, auth_headers, name="供应商B", type="photo")

    resp = await async_client.get("/api/v1/suppliers", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 2


async def test_get_supplier_detail(async_client: AsyncClient, auth_headers):
    """GET /api/v1/suppliers/{id} returns supplier with services and evaluations."""
    supplier = await _create_supplier(async_client, auth_headers)

    # Add a service
    await async_client.post(
        f"/api/v1/suppliers/{supplier['id']}/services",
        headers=auth_headers,
        json={"service_name": "婚礼花艺布置", "price": 8000.0},
    )

    resp = await async_client.get(
        f"/api/v1/suppliers/{supplier['id']}", headers=auth_headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "测试供应商"
    assert len(body["services"]) >= 1


async def test_update_supplier(async_client: AsyncClient, auth_headers):
    """PUT /api/v1/suppliers/{id} updates supplier fields."""
    supplier = await _create_supplier(async_client, auth_headers)

    resp = await async_client.put(
        f"/api/v1/suppliers/{supplier['id']}",
        headers=auth_headers,
        json={"name": "更新后供应商", "contact": "新联系人"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "更新后供应商"
    assert resp.json()["contact"] == "新联系人"


async def test_add_service(async_client: AsyncClient, auth_headers):
    """POST /api/v1/suppliers/{id}/services adds a new service."""
    supplier = await _create_supplier(async_client, auth_headers)

    resp = await async_client.post(
        f"/api/v1/suppliers/{supplier['id']}/services",
        headers=auth_headers,
        json={"service_name": "跟拍套餐", "price": 6000.0, "unit": "套"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["service_name"] == "跟拍套餐"
    assert float(body["price"]) == 6000.0
    assert body["unit"] == "套"


async def test_update_service(async_client: AsyncClient, auth_headers):
    """PUT /api/v1/suppliers/{id}/services/{sid} updates a service."""
    supplier = await _create_supplier(async_client, auth_headers)

    svc_resp = await async_client.post(
        f"/api/v1/suppliers/{supplier['id']}/services",
        headers=auth_headers,
        json={"service_name": "主持服务", "price": 3000.0},
    )
    service_id = svc_resp.json()["id"]

    resp = await async_client.put(
        f"/api/v1/suppliers/{supplier['id']}/services/{service_id}",
        headers=auth_headers,
        json={"price": 3500.0, "service_name": "金牌主持"},
    )
    assert resp.status_code == 200
    assert resp.json()["service_name"] == "金牌主持"
    assert float(resp.json()["price"]) == 3500.0


async def test_add_evaluation(async_client: AsyncClient, auth_headers, test_user):
    """POST /api/v1/suppliers/{id}/evaluations adds an evaluation and updates rating."""
    supplier = await _create_supplier(async_client, auth_headers)
    customer = await _create_customer(async_client, auth_headers)
    order = await _create_order(
        async_client, auth_headers, customer["id"], test_user.id
    )

    resp = await async_client.post(
        f"/api/v1/suppliers/{supplier['id']}/evaluations",
        headers=auth_headers,
        json={"order_id": order["id"], "rating": 5, "content": "非常满意"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["rating"] == 5
    assert body["content"] == "非常满意"


async def test_rating_recalculation(async_client: AsyncClient, auth_headers, test_user):
    """
    Adding multiple evaluations recalculates the average rating on the supplier.
    """
    supplier = await _create_supplier(async_client, auth_headers)

    # Add two orders with different ratings
    for rating_val in [4, 5]:
        customer = await _create_customer(async_client, auth_headers)
        order = await _create_order(
            async_client, auth_headers, customer["id"], test_user.id
        )
        await async_client.post(
            f"/api/v1/suppliers/{supplier['id']}/evaluations",
            headers=auth_headers,
            json={"order_id": order["id"], "rating": rating_val},
        )

    # Fetch supplier detail to check recalculated rating
    detail = await async_client.get(
        f"/api/v1/suppliers/{supplier['id']}", headers=auth_headers
    )
    assert detail.status_code == 200
    # Average of 4 and 5 = 4.5
    assert float(detail.json()["rating"]) >= 4.0
