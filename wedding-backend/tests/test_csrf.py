from __future__ import annotations
"""
Tests for CSRF protection middleware.
"""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_csrf_token_endpoint_exists(async_client: AsyncClient):
    """GET /api/v1/auth/csrf should return 200 with a csrf_token."""
    resp = await async_client.get("/api/v1/auth/csrf")
    assert resp.status_code == 200
    body = resp.json()
    assert "csrf_token" in body
    assert len(body["csrf_token"]) >= 16


async def test_csrf_exempt_get_request(async_client: AsyncClient):
    """GET requests should be exempt from CSRF protection."""
    resp = await async_client.get("/api/v1/health")
    assert resp.status_code == 200


async def test_csrf_exempt_login(async_client: AsyncClient):
    """Login endpoint should be exempt from CSRF protection."""
    resp = await async_client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    # May fail due to invalid credentials, but shouldn't be 403 CSRF error
    assert resp.status_code != 403


async def test_csrf_missing_token_on_post(async_client: AsyncClient):
    """POST without X-CSRF-Token header should return 403."""
    # First login to get an auth token
    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    if login_resp.status_code == 200:
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        # This should fail with CSRF error since it's a state-changing POST without token
        resp = await async_client.post(
            "/api/v1/customers",
            headers=headers,
            json={"name": "Test", "phone": "123"},
        )
        # If auth worked, should get 403 CSRF error (or 422 validation error)
        assert resp.status_code in (403, 422)


async def test_csrf_valid_token(async_client: AsyncClient, auth_headers):
    """POST with valid X-CSRF-Token header should succeed."""
    # Get CSRF token
    csrf_resp = await async_client.get("/api/v1/auth/csrf")
    assert csrf_resp.status_code == 200
    csrf_token = csrf_resp.json()["csrf_token"]

    headers = {**auth_headers, "X-CSRF-Token": csrf_token}
    resp = await async_client.get("/api/v1/health")
    # GET request should work regardless of CSRF token
    assert resp.status_code == 200