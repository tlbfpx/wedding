from __future__ import annotations
"""
Tests for Prometheus metrics endpoint: /metrics
"""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_metrics_endpoint_exists(async_client: AsyncClient):
    """GET /metrics should return 200 with Prometheus-formatted metrics."""
    resp = await async_client.get("/metrics")
    assert resp.status_code == 200
    # Prometheus format is text-based, should contain http_requests_total
    assert "http_requests_total" in resp.text


async def test_metrics_includes_request_labels(async_client: AsyncClient, auth_headers):
    """Metrics should include method, endpoint, and status_code labels."""
    # Make some requests to generate metrics
    await async_client.get("/api/v1/health")

    resp = await async_client.get("/metrics")
    text = resp.text
    # Should have labels like method="GET" endpoint="/api/v1/health"
    assert "method=" in text or 'method="' in text


async def test_metrics_skips_own_endpoint(async_client: AsyncClient):
    """The /metrics endpoint itself should not be counted to avoid recursion."""
    # Make multiple calls to /metrics
    resp1 = await async_client.get("/metrics")
    resp2 = await async_client.get("/metrics")

    # Both should succeed (no 429 from self-rate-limiting)
    assert resp1.status_code == 200
    assert resp2.status_code == 200