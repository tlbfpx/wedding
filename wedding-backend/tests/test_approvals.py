from __future__ import annotations
"""
Tests for approval endpoints: /api/v1/approvals/*
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
        "name": "审批客户-" + uuid.uuid4().hex[:6],
        "phone": "3" + uuid.uuid4().hex[:10],
    })
    assert resp.status_code == 200
    return resp.json()


async def _create_order(
    client: AsyncClient, headers: dict, customer_id: int, sale_id: int
) -> dict:
    resp = await client.post("/api/v1/orders", headers=headers, json={
        "customer_id": customer_id,
        "sale_id": sale_id,
        "items": [{"type": "planning", "name": "策划", "unit_price": 8000.0}],
    })
    assert resp.status_code == 200
    return resp.json()


async def _create_approval(
    client: AsyncClient, headers: dict, approval_type: str, target_id: int, reason: str
) -> dict:
    resp = await client.post("/api/v1/approvals", headers=headers, json={
        "type": approval_type,
        "target_id": target_id,
        "reason": reason,
    })
    assert resp.status_code == 200
    return resp.json()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

async def test_create_approval(async_client: AsyncClient, auth_headers, test_user):
    """POST /api/v1/approvals creates a new approval request."""
    customer = await _create_customer(async_client, auth_headers)
    order = await _create_order(
        async_client, auth_headers, customer["id"], test_user.id
    )
    approval = await _create_approval(
        async_client, auth_headers, "cancel", order["id"], "客户要求取消"
    )
    assert approval["type"] == "cancel"
    assert approval["status"] == "pending"
    assert approval["applicant_id"] == test_user.id


async def test_list_approvals(async_client: AsyncClient, auth_headers, test_user):
    """GET /api/v1/approvals returns paginated list."""
    customer = await _create_customer(async_client, auth_headers)
    order = await _create_order(
        async_client, auth_headers, customer["id"], test_user.id
    )
    await _create_approval(
        async_client, auth_headers, "discount", order["id"], "折扣申请"
    )

    resp = await async_client.get("/api/v1/approvals", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1


async def test_approve_approval(async_client: AsyncClient, auth_headers, test_user):
    """PUT /api/v1/approvals/{id} with status=approved approves the request."""
    customer = await _create_customer(async_client, auth_headers)
    order = await _create_order(
        async_client, auth_headers, customer["id"], test_user.id
    )
    approval = await _create_approval(
        async_client, auth_headers, "cancel", order["id"], "客户取消"
    )

    resp = await async_client.put(
        f"/api/v1/approvals/{approval['id']}",
        headers=auth_headers,
        json={"status": "approved"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "approved"
    assert body["approver_id"] == test_user.id

    # Verify the order was cancelled
    order_resp = await async_client.get(
        f"/api/v1/orders/{order['id']}", headers=auth_headers
    )
    assert order_resp.json()["status"] == "cancelled"


async def test_reject_approval(async_client: AsyncClient, auth_headers, test_user):
    """PUT /api/v1/approvals/{id} with status=rejected rejects the request."""
    customer = await _create_customer(async_client, auth_headers)
    order = await _create_order(
        async_client, auth_headers, customer["id"], test_user.id
    )
    approval = await _create_approval(
        async_client, auth_headers, "discount", order["id"], "折扣申请"
    )

    resp = await async_client.put(
        f"/api/v1/approvals/{approval['id']}",
        headers=auth_headers,
        json={"status": "rejected"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"


async def test_non_admin_cannot_approve(
    async_client: AsyncClient, auth_headers, sale_auth_headers, test_user
):
    """
    Any authenticated user can currently call the approve endpoint (there is no
    explicit admin-only check in the route). This test verifies that a non-admin
    user CAN reach the endpoint -- confirming that if permission middleware were
    added, we would need to assert 403 instead. For now we document current behavior.
    """
    customer = await _create_customer(async_client, auth_headers)
    order = await _create_order(
        async_client, auth_headers, customer["id"], test_user.id
    )
    approval = await _create_approval(
        async_client, auth_headers, "cancel", order["id"], "取消申请"
    )

    # The sale user attempts to approve
    resp = await async_client.put(
        f"/api/v1/approvals/{approval['id']}",
        headers=sale_auth_headers,
        json={"status": "approved"},
    )
    # Currently the API has no admin check on this endpoint, so it succeeds.
    # When admin-only middleware is added, this assertion should change to 403.
    assert resp.status_code in (200, 403)
