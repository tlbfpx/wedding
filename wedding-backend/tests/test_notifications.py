from __future__ import annotations
"""
Tests for notification endpoints: /api/v1/notifications/*
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
        "name": "通知客户-" + uuid.uuid4().hex[:6],
        "phone": "4" + uuid.uuid4().hex[:10],
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

async def test_list_notifications_empty(async_client: AsyncClient, auth_headers):
    """GET /api/v1/notifications returns empty list initially."""
    resp = await async_client.get("/api/v1/notifications", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
    assert body["items"] == []


async def test_get_unread_count_zero(async_client: AsyncClient, auth_headers):
    """GET /api/v1/notifications/unread-count returns 0 when no notifications."""
    resp = await async_client.get("/api/v1/notifications/unread-count", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 0


async def test_mark_as_read(async_client: AsyncClient, auth_headers, test_user):
    """
    PUT /api/v1/notifications/read with ids marks them read.
    We create an approval to trigger a notification, then mark it as read.
    """
    # Create a customer, order, and approval to trigger notifications
    customer = await _create_customer(async_client, auth_headers)
    order = await _create_order(
        async_client, auth_headers, customer["id"], test_user.id
    )
    await _create_approval(
        async_client, auth_headers, "cancel", order["id"], "测试通知"
    )

    # List notifications to get IDs
    list_resp = await async_client.get("/api/v1/notifications", headers=auth_headers)
    assert list_resp.status_code == 200
    body = list_resp.json()
    assert body["total"] >= 1

    notification_id = body["items"][0]["id"]

    # Mark as read
    resp = await async_client.put(
        "/api/v1/notifications/read",
        headers=auth_headers,
        json={"ids": [notification_id]},
    )
    assert resp.status_code == 200

    # Verify it's now read
    list_resp2 = await async_client.get(
        "/api/v1/notifications?is_read=true", headers=auth_headers
    )
    assert list_resp2.status_code == 200
    read_items = [n for n in list_resp2.json()["items"] if n["id"] == notification_id]
    assert len(read_items) == 1
    assert read_items[0]["is_read"] is True


async def test_mark_all_as_read(async_client: AsyncClient, auth_headers, test_user):
    """
    PUT /api/v1/notifications/read-all marks all notifications as read.
    """
    # Create notifications via approvals
    customer = await _create_customer(async_client, auth_headers)
    order = await _create_order(
        async_client, auth_headers, customer["id"], test_user.id
    )
    await _create_approval(
        async_client, auth_headers, "cancel", order["id"], "测试全部已读1"
    )

    customer2 = await _create_customer(async_client, auth_headers)
    order2 = await _create_order(
        async_client, auth_headers, customer2["id"], test_user.id
    )
    await _create_approval(
        async_client, auth_headers, "discount", order2["id"], "测试全部已读2"
    )

    # Confirm we have unread notifications
    count_resp = await async_client.get(
        "/api/v1/notifications/unread-count", headers=auth_headers
    )
    assert count_resp.status_code == 200
    assert count_resp.json()["count"] >= 1

    # Mark all as read
    resp = await async_client.put(
        "/api/v1/notifications/read-all", headers=auth_headers
    )
    assert resp.status_code == 200

    # Verify unread count is now 0
    count_resp2 = await async_client.get(
        "/api/v1/notifications/unread-count", headers=auth_headers
    )
    assert count_resp2.status_code == 200
    assert count_resp2.json()["count"] == 0


async def test_notification_created_on_approval(
    async_client: AsyncClient, auth_headers, test_user
):
    """
    POST /api/v1/approvals creates a notification for the approval.
    The on_approval_created handler sends a notification to management users.
    """
    customer = await _create_customer(async_client, auth_headers)
    order = await _create_order(
        async_client, auth_headers, customer["id"], test_user.id
    )
    await _create_approval(
        async_client, auth_headers, "cancel", order["id"], "通知测试"
    )

    # Check that notifications were created
    resp = await async_client.get("/api/v1/notifications", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1

    # Verify the notification content
    notification = body["items"][0]
    assert "审批" in notification["title"]
    assert notification["type"] == "approval"
    assert notification["is_read"] is False
