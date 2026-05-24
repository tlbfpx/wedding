from __future__ import annotations
"""
Tests for health check endpoints: /api/v1/health, /api/v1/ready
"""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_liveness_returns_ok(async_client: AsyncClient):
    """GET /api/v1/health returns 200 with status ok (no DB/Redis required)."""
    resp = await async_client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"


async def test_readiness_returns_service_status(async_client: AsyncClient):
    """GET /api/v1/ready returns service status (may be degraded in test env)."""
    resp = await async_client.get("/api/v1/ready")
    assert resp.status_code == 200
    body = resp.json()
    # In test environment, MySQL/Redis may not be available
    assert body["status"] in ("ok", "degraded")
    assert "services" in body
    assert "mysql" in body["services"]
    assert "redis" in body["services"]


async def test_health_excluded_from_rate_limit(async_client: AsyncClient):
    """Health endpoints should be accessible even under rate limit."""
    # Hit health endpoint multiple times rapidly
    for _ in range(10):
        resp = await async_client.get("/api/v1/health")
        assert resp.status_code == 200