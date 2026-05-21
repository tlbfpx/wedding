"""
Tests for system management endpoints: /api/v1/users/*
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, Role
from app.models.user import TeamEnum, UserStatus


pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

async def test_create_user(async_client: AsyncClient, auth_headers, test_role):
    """POST /api/v1/users creates a new user."""
    resp = await async_client.post("/api/v1/users", headers=auth_headers, json={
        "username": "newuser",
        "password": "newpass123",
        "name": "New User",
        "phone": "15800001111",
        "role_id": test_role.id,
        "team": "sales",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["username"] == "newuser"
    assert body["name"] == "New User"
    assert body["team"] == "sales"
    assert body["status"] == "active"
    assert "password_hash" not in body  # Should not expose password hash


async def test_list_users(async_client: AsyncClient, auth_headers, test_user):
    """GET /api/v1/users returns paginated user list."""
    resp = await async_client.get("/api/v1/users", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    assert any(u["username"] == "admin" for u in body["items"])


async def test_update_user(
    async_client: AsyncClient, auth_headers, test_user, test_role
):
    """PUT /api/v1/users/{id} updates user fields."""
    # Create a user to update
    create_resp = await async_client.post("/api/v1/users", headers=auth_headers, json={
        "username": "update_me",
        "password": "pass123",
        "name": "Before Update",
        "role_id": test_role.id,
        "team": "planning",
    })
    user_id = create_resp.json()["id"]

    resp = await async_client.put(
        f"/api/v1/users/{user_id}",
        headers=auth_headers,
        json={"name": "After Update", "phone": "15900009999"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "After Update"
    assert resp.json()["phone"] == "15900009999"


async def test_list_roles(async_client: AsyncClient, auth_headers, test_role):
    """GET /api/v1/users/roles returns all roles."""
    resp = await async_client.get("/api/v1/users/roles", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) >= 1
    assert any(r["name"] == "管理员" for r in body)


async def test_update_role_permissions(async_client: AsyncClient, auth_headers, test_role):
    """PUT /api/v1/users/roles/{id} updates role name and permissions."""
    new_perms = {
        "customer": {"read": "all", "write": "own"},
        "order": {"read": "all", "write": "none"},
    }

    resp = await async_client.put(
        f"/api/v1/users/roles/{test_role.id}",
        headers=auth_headers,
        json={"name": "高级管理员", "permissions": new_perms},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "高级管理员"
    assert body["permissions"]["customer"]["write"] == "own"


async def test_operation_logs(
    async_client: AsyncClient, auth_headers, test_user, test_role
):
    """GET /api/v1/users/operation-logs returns paginated log entries."""
    # Performing a write operation should generate a log entry
    await async_client.post("/api/v1/users", headers=auth_headers, json={
        "username": "log_test_user",
        "password": "pass123",
        "name": "Log Test",
        "role_id": test_role.id,
        "team": "sales",
    })

    resp = await async_client.get(
        "/api/v1/users/operation-logs", headers=auth_headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    # Each log should have expected fields
    log = body["items"][0]
    assert "user_id" in log
    assert "module" in log
    assert "action" in log
    assert "created_at" in log
