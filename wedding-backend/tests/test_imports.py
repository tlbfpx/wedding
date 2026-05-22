from __future__ import annotations
"""
Tests for data import endpoints: /api/v1/imports/*
"""

import io

import pytest
from httpx import AsyncClient
from openpyxl import Workbook


pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_customer_xlsx():
    wb = Workbook()
    ws = wb.active
    ws.append(["姓名", "手机号", "性别", "来源", "预算范围", "婚期", "备注"])
    ws.append(["测试客户", "13900001111", "男", "线上", "5-10万", "2026-10-01", "测试导入"])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


def _make_supplier_xlsx():
    wb = Workbook()
    ws = wb.active
    ws.append(["名称", "类型", "联系人", "联系电话", "地址", "合作状态", "备注"])
    ws.append(["测试供应商", "花艺", "张三", "13800002222", "北京市", "合作中", "测试导入"])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

async def test_download_customer_template(async_client: AsyncClient, auth_headers):
    """GET /api/v1/imports/template?import_type=customer returns xlsx."""
    resp = await async_client.get(
        "/api/v1/imports/template?import_type=customer", headers=auth_headers
    )
    assert resp.status_code == 200
    assert (
        resp.headers["content-type"]
        == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert len(resp.content) > 0


async def test_download_supplier_template(async_client: AsyncClient, auth_headers):
    """GET /api/v1/imports/template?import_type=supplier returns xlsx."""
    resp = await async_client.get(
        "/api/v1/imports/template?import_type=supplier", headers=auth_headers
    )
    assert resp.status_code == 200
    assert (
        resp.headers["content-type"]
        == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert len(resp.content) > 0


async def test_import_customers_success(async_client: AsyncClient, auth_headers):
    """POST /api/v1/imports/upload?import_type=customer with valid file imports data."""
    buf = _make_customer_xlsx()
    files = {
        "file": (
            "customers.xlsx",
            buf,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    }
    resp = await async_client.post(
        "/api/v1/imports/upload?import_type=customer",
        headers=auth_headers,
        files=files,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["success"] == 1
    assert body["failed"] == 0


async def test_import_invalid_type(async_client: AsyncClient, auth_headers):
    """GET /api/v1/imports/template?import_type=invalid returns 400."""
    resp = await async_client.get(
        "/api/v1/imports/template?import_type=invalid", headers=auth_headers
    )
    assert resp.status_code == 400
    body = resp.json()
    assert body["error"]["code"] == "INVALID_TYPE"
