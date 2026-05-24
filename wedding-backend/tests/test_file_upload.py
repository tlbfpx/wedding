from __future__ import annotations
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
    Uploading a non-PDF file to the contract endpoint should be rejected.
    """
    customer = await _create_customer(async_client, auth_headers)
    order = await _create_order(
        async_client, auth_headers, customer["id"], test_user.id
    )

    # Upload a text file with wrong extension - should be rejected due to magic bytes mismatch
    fake_content = b"not a valid file content"
    files = {"file": ("contract.txt", BytesIO(fake_content), "text/plain")}

    resp = await async_client.post(
        f"/api/v1/orders/{order['id']}/contract",
        headers=auth_headers,
        files=files,
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "INVALID_FILE_TYPE"


async def test_upload_mismatched_mime_type(async_client: AsyncClient, auth_headers, test_user):
    """
    Uploading a file that claims to be PDF but has wrong magic bytes should be rejected.
    """
    customer = await _create_customer(async_client, auth_headers)
    order = await _create_order(
        async_client, auth_headers, customer["id"], test_user.id
    )

    # Content is not a PDF but claims to be in content_type
    fake_pdf_content = b"This is not a real PDF file"
    files = {"file": ("fake.pdf", BytesIO(fake_pdf_content), "application/pdf")}

    resp = await async_client.post(
        f"/api/v1/orders/{order['id']}/contract",
        headers=auth_headers,
        files=files,
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "INVALID_FILE_TYPE"


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


async def test_upload_filename_path_traversal(async_client: AsyncClient, auth_headers, test_user):
    """
    Filenames with path traversal characters should be sanitized.
    """
    customer = await _create_customer(async_client, auth_headers)
    order = await _create_order(
        async_client, auth_headers, customer["id"], test_user.id
    )

    pdf_content = b"%PDF-1.4 fake pdf content for testing"
    files = {
        "file": (
            "../../../etc/passwd",
            BytesIO(pdf_content),
            "application/pdf"
        )
    }

    resp = await async_client.post(
        f"/api/v1/orders/{order['id']}/contract",
        headers=auth_headers,
        files=files,
    )
    # Should succeed but filename should be sanitized (no path traversal)
    assert resp.status_code == 200
    file_url = resp.json()["file_url"]
    # The file_url should not contain ".." segments
    assert ".." not in file_url


async def test_upload_filename_special_chars(async_client: AsyncClient, auth_headers, test_user):
    """
    Filenames with special characters should be sanitized.
    """
    customer = await _create_customer(async_client, auth_headers)
    order = await _create_order(
        async_client, auth_headers, customer["id"], test_user.id
    )

    pdf_content = b"%PDF-1.4 fake pdf content for testing"
    files = {
        "file": (
            "合同<special>:chars|.pdf",
            BytesIO(pdf_content),
            "application/pdf"
        )
    }

    resp = await async_client.post(
        f"/api/v1/orders/{order['id']}/contract",
        headers=auth_headers,
        files=files,
    )
    # Should succeed with sanitized filename
    assert resp.status_code == 200
    file_url = resp.json()["file_url"]
    # Should not contain special path characters
    assert "<" not in file_url
    assert ">" not in file_url
    assert ":" not in file_url
    assert "|" not in file_url
