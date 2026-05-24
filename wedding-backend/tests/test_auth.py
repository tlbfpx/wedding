from __future__ import annotations
"""
Tests for authentication endpoints: /api/v1/auth/*
"""

import pytest
from httpx import AsyncClient


pytestmark = pytest.mark.asyncio


async def test_login_success(async_client: AsyncClient, test_user):
    """POST /api/v1/auth/login returns tokens on valid credentials."""
    resp = await async_client.post("/api/v1/auth/login", json={
        "username": "admin",
        "password": "testpass123",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["token_type"] == "bearer"


async def test_login_invalid_password(async_client: AsyncClient, test_user):
    """POST /api/v1/auth/login returns 401 on wrong password."""
    resp = await async_client.post("/api/v1/auth/login", json={
        "username": "admin",
        "password": "wrong_password",
    })
    assert resp.status_code == 401
    assert resp.json()["detail"]["code"] == "INVALID_CREDENTIALS"


async def test_login_account_locked(async_client: AsyncClient, test_user):
    """POST /api/v1/auth/login returns 403 after 5 failed attempts."""
    # Simulate 5 failed login attempts with same username
    for i in range(5):
        await async_client.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "wrong",
        })

    # The 6th attempt should be locked
    resp = await async_client.post("/api/v1/auth/login", json={
        "username": "admin",
        "password": "testpass123",
    })
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "ACCOUNT_LOCKED"


async def test_refresh_token(async_client: AsyncClient, test_user):
    """POST /api/v1/auth/refresh returns a new access token."""
    from app.utils.auth import create_refresh_token
    refresh_token = create_refresh_token({"sub": str(test_user.id)})

    resp = await async_client.post("/api/v1/auth/refresh", json={
        "refresh_token": refresh_token,
    })
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


async def test_logout(async_client: AsyncClient, auth_headers):
    """POST /api/v1/auth/logout returns success message."""
    resp = await async_client.post("/api/v1/auth/logout", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["message"] == "已登出"


async def test_get_me(async_client: AsyncClient, auth_headers, test_user):
    """GET /api/v1/auth/me returns current user info."""
    resp = await async_client.get("/api/v1/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == test_user.id
    assert body["username"] == "admin"
    assert body["name"] == "Test Admin"
    assert "permissions" in body


async def test_unauthorized_access(async_client: AsyncClient):
    """Requests without a token should be rejected with 401 or 403."""
    resp = await async_client.get("/api/v1/auth/me")
    assert resp.status_code in (401, 403)


async def test_logout_blacklists_token(async_client: AsyncClient, auth_headers):
    """POST /api/v1/auth/logout should blacklist the access token."""
    # First logout
    resp = await async_client.post("/api/v1/auth/logout", headers=auth_headers)
    assert resp.status_code == 200

    # Try using the same token - should be rejected
    resp2 = await async_client.get("/api/v1/auth/me", headers=auth_headers)
    assert resp2.status_code == 401


async def test_refresh_token_rotation(async_client: AsyncClient, test_user):
    """POST /api/v1/auth/refresh should issue a new refresh token (rotation)."""
    from app.utils.auth import create_refresh_token
    refresh_token = create_refresh_token({"sub": str(test_user.id)})

    resp1 = await async_client.post("/api/v1/auth/refresh", json={
        "refresh_token": refresh_token,
    })
    assert resp1.status_code == 200
    body1 = resp1.json()
    assert "refresh_token" in body1
    first_refresh = body1["refresh_token"]

    # Use the new refresh token - should get another new one
    resp2 = await async_client.post("/api/v1/auth/refresh", json={
        "refresh_token": first_refresh,
    })
    assert resp2.status_code == 200
    body2 = resp2.json()
    assert "refresh_token" in body2

    # Old refresh token should not work (rotation)
    resp3 = await async_client.post("/api/v1/auth/refresh", json={
        "refresh_token": refresh_token,
    })
    assert resp3.status_code == 401
    assert resp3.json()["detail"]["code"] == "TOKEN_REUSED"


async def test_refresh_token_reuse_detected(async_client: AsyncClient, test_user):
    """Reusing an already-used refresh token should return 401 and revoke tokens."""
    from app.utils.auth import create_refresh_token
    refresh_token = create_refresh_token({"sub": str(test_user.id)})

    # First use - should succeed
    resp1 = await async_client.post("/api/v1/auth/refresh", json={
        "refresh_token": refresh_token,
    })
    assert resp1.status_code == 200

    # Reuse of same token - should fail with TOKEN_REUSED
    resp2 = await async_client.post("/api/v1/auth/refresh", json={
        "refresh_token": refresh_token,
    })
    assert resp2.status_code == 401
    assert resp2.json()["detail"]["code"] == "TOKEN_REUSED"
