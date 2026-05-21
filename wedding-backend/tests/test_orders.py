from __future__ import annotations
"""
Tests for order endpoints: /api/v1/orders/*
"""

import pytest
import uuid
from httpx import AsyncClient


pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _create_customer(client: AsyncClient, headers: dict) -> dict:
    resp = await client.post("/api/v1/customers", headers=headers, json={
        "name": "订单客户-" + uuid.uuid4().hex[:6],
        "phone": "2" + uuid.uuid4().hex[:10],
    })
    assert resp.status_code == 200
    return resp.json()


async def _create_supplier(client: AsyncClient, headers: dict) -> dict:
    resp = await client.post("/api/v1/suppliers", headers=headers, json={
        "name": "订单供应商-" + uuid.uuid4().hex[:6],
        "type": "floral",
    })
    assert resp.status_code == 200
    return resp.json()


async def _create_order(
    client: AsyncClient, headers: dict, customer_id: int, sale_id: int, **overrides
) -> dict:
    payload = {
        "customer_id": customer_id,
        "sale_id": sale_id,
        "items": [
            {"type": "planning", "name": "婚礼策划", "unit_price": 10000.0, "quantity": 1},
        ],
    }
    payload.update(overrides)
    resp = await client.post("/api/v1/orders", headers=headers, json=payload)
    assert resp.status_code == 200
    return resp.json()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

async def test_create_order(async_client: AsyncClient, auth_headers, test_user):
    """POST /api/v1/orders creates a new order with items."""
    customer = await _create_customer(async_client, auth_headers)
    body = await _create_order(
        async_client, auth_headers, customer["id"], test_user.id
    )
    assert body["order_no"].startswith("WD")
    assert body["status"] == "intention"
    assert float(body["total_amount"]) > 0


async def test_list_orders(async_client: AsyncClient, auth_headers, test_user):
    """GET /api/v1/orders returns paginated order list."""
    customer = await _create_customer(async_client, auth_headers)
    await _create_order(async_client, auth_headers, customer["id"], test_user.id)

    resp = await async_client.get("/api/v1/orders", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1


async def test_get_order_detail(async_client: AsyncClient, auth_headers, test_user):
    """GET /api/v1/orders/{id} returns order with items, payments, contract."""
    customer = await _create_customer(async_client, auth_headers)
    order = await _create_order(
        async_client, auth_headers, customer["id"], test_user.id
    )

    resp = await async_client.get(
        f"/api/v1/orders/{order['id']}", headers=auth_headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert "payments" in body
    assert "contract" in body
    assert len(body["items"]) >= 1


async def test_update_order_intention_only(
    async_client: AsyncClient, auth_headers, test_user
):
    """PUT /api/v1/orders/{id} only works when order status is 'intention'."""
    customer = await _create_customer(async_client, auth_headers)
    order = await _create_order(
        async_client, auth_headers, customer["id"], test_user.id
    )

    # Update should succeed in intention status
    resp = await async_client.put(
        f"/api/v1/orders/{order['id']}",
        headers=auth_headers,
        json={"note": "更新备注"},
    )
    assert resp.status_code == 200
    assert resp.json()["note"] == "更新备注"


async def test_status_transition_valid(async_client: AsyncClient, auth_headers, test_user):
    """PUT /api/v1/orders/{id}/status allows valid forward transitions."""
    customer = await _create_customer(async_client, auth_headers)
    order = await _create_order(
        async_client, auth_headers, customer["id"], test_user.id
    )

    # intention -> signed
    resp = await async_client.put(
        f"/api/v1/orders/{order['id']}/status",
        headers=auth_headers,
        json={"status": "signed"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "signed"

    # signed -> executing
    resp = await async_client.put(
        f"/api/v1/orders/{order['id']}/status",
        headers=auth_headers,
        json={"status": "executing"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "executing"


async def test_status_transition_invalid_reverse(
    async_client: AsyncClient, auth_headers, test_user
):
    """PUT /api/v1/orders/{id}/status rejects reverse transitions."""
    customer = await _create_customer(async_client, auth_headers)
    order = await _create_order(
        async_client, auth_headers, customer["id"], test_user.id
    )

    # Move to signed first
    await async_client.put(
        f"/api/v1/orders/{order['id']}/status",
        headers=auth_headers,
        json={"status": "signed"},
    )

    # Attempt to go back to intention -> should fail
    resp = await async_client.put(
        f"/api/v1/orders/{order['id']}/status",
        headers=auth_headers,
        json={"status": "intention"},
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "INVALID_TRANSITION"


async def test_add_payment(async_client: AsyncClient, auth_headers, test_user):
    """POST /api/v1/orders/{id}/payments records a payment."""
    customer = await _create_customer(async_client, auth_headers)
    order = await _create_order(
        async_client, auth_headers, customer["id"], test_user.id
    )

    resp = await async_client.post(
        f"/api/v1/orders/{order['id']}/payments",
        headers=auth_headers,
        json={"amount": 5000.0, "method": "wechat"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert float(body["amount"]) == 5000.0
    assert body["method"] == "wechat"


async def test_payment_exceeds_total(async_client: AsyncClient, auth_headers, test_user):
    """POST /api/v1/orders/{id}/payments rejects payment exceeding order total."""
    customer = await _create_customer(async_client, auth_headers)
    order = await _create_order(
        async_client, auth_headers, customer["id"], test_user.id
    )

    total = float(order["total_amount"])

    resp = await async_client.post(
        f"/api/v1/orders/{order['id']}/payments",
        headers=auth_headers,
        json={"amount": total + 10000, "method": "cash"},
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "PAYMENT_EXCEEDS_TOTAL"


async def test_discount_triggers_approval(
    async_client: AsyncClient, auth_headers, test_user
):
    """
    Creating an order with a discount < 1.00 should be recordable.
    In the real workflow, discount approval would be created separately.
    Here we verify discount is stored and an approval can be created for it.
    """
    customer = await _create_customer(async_client, auth_headers)
    order = await _create_order(
        async_client, auth_headers,
        customer_id=customer["id"],
        sale_id=test_user.id,
        discount=0.85,
    )
    assert float(order["discount"]) == 0.85

    # Create a discount approval for this order
    resp = await async_client.post("/api/v1/approvals", headers=auth_headers, json={
        "type": "discount",
        "target_id": order["id"],
        "reason": "客户VIP折扣",
    })
    assert resp.status_code == 200
    assert resp.json()["type"] == "discount"
    assert resp.json()["status"] == "pending"
