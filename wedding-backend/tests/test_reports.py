from __future__ import annotations
"""
Tests for report export endpoints: /api/v1/reports/export
"""

import pytest

from httpx import AsyncClient


pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

async def test_export_order_report(async_client: AsyncClient, auth_headers):
    """GET /api/v1/reports/export?report_type=order returns xlsx file."""
    resp = await async_client.get(
        "/api/v1/reports/export?report_type=order", headers=auth_headers
    )
    assert resp.status_code == 200
    assert (
        resp.headers["content-type"]
        == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert len(resp.content) > 0


async def test_export_customer_report(async_client: AsyncClient, auth_headers):
    """GET /api/v1/reports/export?report_type=customer returns xlsx file."""
    resp = await async_client.get(
        "/api/v1/reports/export?report_type=customer", headers=auth_headers
    )
    assert resp.status_code == 200
    assert (
        resp.headers["content-type"]
        == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert len(resp.content) > 0


async def test_export_finance_report(async_client: AsyncClient, auth_headers):
    """GET /api/v1/reports/export?report_type=finance returns xlsx file."""
    resp = await async_client.get(
        "/api/v1/reports/export?report_type=finance", headers=auth_headers
    )
    assert resp.status_code == 200
    assert (
        resp.headers["content-type"]
        == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert len(resp.content) > 0


async def test_export_invalid_type(async_client: AsyncClient, auth_headers):
    """GET /api/v1/reports/export?report_type=invalid returns 400."""
    resp = await async_client.get(
        "/api/v1/reports/export?report_type=invalid", headers=auth_headers
    )
    assert resp.status_code == 400
    body = resp.json()
    assert body["error"]["code"] == "INVALID_TYPE"


async def test_export_with_filters(async_client: AsyncClient, auth_headers):
    """GET /api/v1/reports/export with date filters returns xlsx file."""
    resp = await async_client.get(
        "/api/v1/reports/export?report_type=order&date_start=2026-01-01&date_end=2026-12-31",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert (
        resp.headers["content-type"]
        == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert len(resp.content) > 0
