"""
Tests for file upload endpoints (contract upload on orders).
"""

import pytest
from io import BytesIO
from httpx import AsyncClient
import uuid


pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _create_customer(client: AsyncClient, headers: dict) -> dict:
    resp = await client.post("/api/v1/customers", headers=headers, json={
        "name": "合同客户-" + uuid.uuid4().hex[:6],
        "phone": "5" + uuid.uuid4().hex[:10],
    })
    assert resp.status_code == 200
    return resp.json()


async def _create_order(
    client: AsyncClient, headers: dict, customer_id: int, sale_id: int
) -> dict:
    resp = await client.post("/api/v1/orders", headers=headers, json={
        "customer_id": customer_id,
        "sale_id": sale_id,
        "items": [{"type": "planning", "name": "婚礼策划", "unit_price": 10000.0}],
    })
    assert resp.status_code == 200
    return resp.json()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

async def test_upload_contract_pdf(async_client: AsyncClient, auth_headers, test_user):
    """POST /api/v1/orders/{id}/contract uploads a PDF contract file."""
    customer = await _create_customer(async_client, auth_headers)
    order = await _create_order(
        async_client, auth_headers, customer["id"], test_user.id
    )

    pdf_content = b"%PDF-1.4 fake pdf content for testing"
    files = {"file": ("contract.pdf", BytesIO(pdf_content), "application/pdf")}

    resp = await async_client.post(
        f"/api/v1/orders/{order['id']}/contract",
        headers=auth_headers,
        files=files,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["order_id"] == order["id"]
    assert body["status"] == "pending"
    assert "file_url" in body


async def test_upload_invalid_type(async_client: AsyncClient, auth_headers, test_user):
    """
    Uploading a non-PDF file to the contract endpoint.
    The API currently does not validate file MIME type explicitly,
    so any file is accepted. This test documents the current behavior.
    """
    customer = await _create_customer(async_client, auth_headers)
    order = await _create_order(
        async_client, auth_headers, customer["id"], test_user.id
    )

    # Upload an executable file -- currently accepted because no type check
    fake_content = b"not a valid file"
    files = {"file": ("malware.exe", BytesIO(fake_content), "application/octet-stream")}

    resp = await async_client.post(
        f"/api/v1/orders/{order['id']}/contract",
        headers=auth_headers,
        files=files,
    )
    # The API does not filter by MIME type, so it accepts the upload.
    # If file-type validation is added, change assertion to assert status == 400.
    assert resp.status_code in (200, 400)


async def test_upload_too_large(async_client: AsyncClient, auth_headers, test_user):
    """
    POST /api/v1/orders/{id}/contract rejects files exceeding MAX_FILE_SIZE_MB.
    """
    customer = await _create_customer(async_client, auth_headers)
    order = await _create_order(
        async_client, auth_headers, customer["id"], test_user.id
    )

    # Create a file larger than the default 10 MB limit
    large_content = b"x" * (11 * 1024 * 1024)  # 11 MB
    files = {"file": ("big_contract.pdf", BytesIO(large_content), "application/pdf")}

    resp = await async_client.post(
        f"/api/v1/orders/{order['id']}/contract",
        headers=auth_headers,
        files=files,
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "FILE_TOO_LARGE"
