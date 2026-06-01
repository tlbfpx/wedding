"""Integration tests for the finance module API endpoints."""

import pytest
from httpx import AsyncClient


pytestmark = pytest.mark.asyncio


async def test_list_receivables_empty(async_client: AsyncClient, auth_headers: dict):
    resp = await async_client.get("/api/v1/finance/receivables", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["items"] == []
    assert resp.json()["total"] == 0


async def test_list_overdue_receivables(async_client: AsyncClient, auth_headers: dict):
    resp = await async_client.get("/api/v1/finance/receivables/overdue", headers=auth_headers)
    assert resp.status_code == 200
    assert "items" in resp.json()


async def test_list_payments_empty(async_client: AsyncClient, auth_headers: dict):
    resp = await async_client.get("/api/v1/finance/payments", headers=auth_headers)
    assert resp.status_code == 200
    assert "items" in resp.json()


async def test_list_refunds_empty(async_client: AsyncClient, auth_headers: dict):
    resp = await async_client.get("/api/v1/finance/refunds", headers=auth_headers)
    assert resp.status_code == 200
    assert "items" in resp.json()


async def test_transactions_list(async_client: AsyncClient, auth_headers: dict):
    resp = await async_client.get("/api/v1/finance/transactions", headers=auth_headers)
    assert resp.status_code == 200
    assert "items" in resp.json()


async def test_create_expense_transaction(async_client: AsyncClient, auth_headers: dict):
    resp = await async_client.post(
        "/api/v1/finance/transactions",
        json={"category": "other", "amount": 1500, "note": "测试支出"},
        headers=auth_headers,
    )
    assert resp.status_code in (200, 201)
    txn = resp.json()
    assert txn["type"] == "expense"
    assert float(txn["amount"]) == 1500.0
    assert txn["category"] == "other"


async def test_transaction_summary(async_client: AsyncClient, auth_headers: dict):
    resp = await async_client.get(
        "/api/v1/finance/transactions/summary",
        params={"start_date": "2026-01-01", "end_date": "2026-12-31"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "income_total" in data
    assert "expense_total" in data
    assert "net_amount" in data


async def test_list_invoices_empty(async_client: AsyncClient, auth_headers: dict):
    resp = await async_client.get("/api/v1/finance/invoices", headers=auth_headers)
    assert resp.status_code == 200
    assert "items" in resp.json()


async def test_reconciliation_report(async_client: AsyncClient, auth_headers: dict):
    resp = await async_client.get(
        "/api/v1/finance/reconciliations/report",
        params={"period": "2026-05"},
        headers=auth_headers,
    )
    assert resp.status_code == 200


async def test_reconciliation_history(async_client: AsyncClient, auth_headers: dict):
    resp = await async_client.get(
        "/api/v1/finance/reconciliations/history",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert "items" in resp.json()


async def test_finance_permission_denied(async_client: AsyncClient, sale_auth_headers: dict):
    """Sale user without finance permission should be denied."""
    resp = await async_client.get(
        "/api/v1/finance/receivables",
        headers=sale_auth_headers,
    )
    assert resp.status_code == 403


async def test_payment_validation(async_client: AsyncClient, auth_headers: dict):
    """Payment with invalid data should be rejected."""
    resp = await async_client.post(
        "/api/v1/finance/payments",
        json={"order_id": 99999, "amount": -100, "method": "transfer"},
        headers=auth_headers,
    )
    assert resp.status_code in (400, 404, 422, 500)
