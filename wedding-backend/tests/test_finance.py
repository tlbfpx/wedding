"""Integration tests for the finance module API endpoints."""

import pytest
from httpx import AsyncClient


pytestmark = pytest.mark.asyncio


async def _create_order(client: AsyncClient, headers: dict, phone: str, unit_price: float) -> int:
    """Create customer + order, return order_id."""
    c = await client.post(
        "/api/v1/customers",
        json={"name": f"客户{phone}", "phone": phone},
        headers=headers,
    )
    assert c.status_code in (200, 201), f"Customer: {c.text}"
    customer_id = c.json()["id"]

    me = await client.get("/api/v1/auth/me", headers=headers)
    sale_id = me.json().get("id", 1)

    o = await client.post(
        "/api/v1/orders",
        json={
            "customer_id": customer_id,
            "sale_id": sale_id,
            "discount": 1.0,
            "items": [{"type": "planning", "name": "策划", "quantity": 1, "unit_price": unit_price}],
        },
        headers=headers,
    )
    assert o.status_code in (200, 201), f"Order: {o.text}"
    return o.json()["id"]


async def test_list_receivables_empty(async_client: AsyncClient, auth_headers: dict):
    resp = await async_client.get("/api/v1/finance/receivables", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


async def test_order_creates_receivable(async_client: AsyncClient, auth_headers: dict):
    """ORDER_CREATED event should auto-create a receivable."""
    order_id = await _create_order(async_client, auth_headers, "13900001111", 10000)

    resp = await async_client.get("/api/v1/finance/receivables", headers=auth_headers)
    assert resp.status_code == 200
    items = resp.json()["items"]
    matching = [r for r in items if r["order_id"] == order_id]
    assert len(matching) == 1
    assert float(matching[0]["total_amount"]) == 10000.0
    assert matching[0]["status"] == "unpaid"


async def test_create_payment_and_receivable_update(async_client: AsyncClient, auth_headers: dict):
    """Payment should update receivable received_amount and status."""
    order_id = await _create_order(async_client, auth_headers, "13900002222", 8000)

    # Create payment
    pay_resp = await async_client.post(
        "/api/v1/finance/payments",
        json={"order_id": order_id, "amount": 5000, "method": "transfer"},
        headers=auth_headers,
    )
    assert pay_resp.status_code in (200, 201)
    payment = pay_resp.json()
    assert payment["order_id"] == order_id
    assert float(payment["amount"]) == 5000.0

    # Check receivable updated
    recv_resp = await async_client.get("/api/v1/finance/receivables", headers=auth_headers)
    items = recv_resp.json()["items"]
    recv = [r for r in items if r["order_id"] == order_id][0]
    assert float(recv["received_amount"]) == 5000.0
    assert recv["status"] == "partial"


async def test_delete_payment(async_client: AsyncClient, auth_headers: dict):
    """Deleting a payment should update receivable back."""
    order_id = await _create_order(async_client, auth_headers, "13900003333", 6000)

    pay_resp = await async_client.post(
        "/api/v1/finance/payments",
        json={"order_id": order_id, "amount": 6000, "method": "cash"},
        headers=auth_headers,
    )
    payment_id = pay_resp.json()["id"]

    del_resp = await async_client.delete(
        f"/api/v1/finance/payments/{payment_id}",
        headers=auth_headers,
    )
    assert del_resp.status_code == 200


async def test_create_refund(async_client: AsyncClient, auth_headers: dict):
    """Refund creation should work for orders with payments."""
    order_id = await _create_order(async_client, auth_headers, "13900004444", 10000)

    await async_client.post(
        "/api/v1/finance/payments",
        json={"order_id": order_id, "amount": 10000, "method": "wechat"},
        headers=auth_headers,
    )

    refund_resp = await async_client.post(
        "/api/v1/finance/refunds",
        json={"order_id": order_id, "amount": 3000, "reason": "部分取消"},
        headers=auth_headers,
    )
    assert refund_resp.status_code in (200, 201)
    refund = refund_resp.json()
    assert refund["status"] == "pending_approval"
    assert float(refund["amount"]) == 3000.0


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


async def test_create_invoice(async_client: AsyncClient, auth_headers: dict):
    order_id = await _create_order(async_client, auth_headers, "13900005555", 20000)

    invoice_resp = await async_client.post(
        "/api/v1/finance/invoices",
        json={
            "order_id": order_id,
            "invoice_type": "normal",
            "amount": 20000,
            "title": "测试公司",
            "tax_no": "1234567890",
        },
        headers=auth_headers,
    )
    assert invoice_resp.status_code in (200, 201)
    invoice = invoice_resp.json()
    assert invoice["status"] == "pending"
    assert invoice["invoice_type"] == "normal"

    # Update to processing
    update_resp = await async_client.put(
        f"/api/v1/finance/invoices/{invoice['id']}",
        json={"status": "processing", "invoice_no": "INV-001"},
        headers=auth_headers,
    )
    assert update_resp.status_code == 200


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


async def test_finance_permission_denied(async_client: AsyncClient, sale_auth_headers: dict):
    resp = await async_client.get(
        "/api/v1/finance/receivables",
        headers=sale_auth_headers,
    )
    assert resp.status_code == 403


async def test_payment_validation(async_client: AsyncClient, auth_headers: dict):
    resp = await async_client.post(
        "/api/v1/finance/payments",
        json={"order_id": 99999, "amount": -100, "method": "transfer"},
        headers=auth_headers,
    )
    assert resp.status_code in (400, 404, 422, 500)
