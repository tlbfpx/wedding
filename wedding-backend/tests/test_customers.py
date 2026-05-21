"""
Tests for customer endpoints: /api/v1/customers/*
"""

import pytest
from datetime import date
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer, CustomerSource, CustomerStatus


pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _create_source(db: AsyncSession) -> CustomerSource:
    source = CustomerSource(name="线上渠道")
    db.add(source)
    await db.commit()
    await db.refresh(source)
    return source


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

async def test_create_customer(
    async_client: AsyncClient, auth_headers, test_user, db_session
):
    """POST /api/v1/customers creates a new customer."""
    source = await _create_source(db_session)
    resp = await async_client.post("/api/v1/customers", headers=auth_headers, json={
        "name": "张三",
        "phone": "13900001111",
        "gender": "male",
        "budget_range": "5-10万",
        "wedding_date": "2025-10-01",
        "source_id": source.id,
        "note": "测试客户",
        "assigned_sale_id": test_user.id,
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "张三"
    assert body["phone"] == "13900001111"
    assert body["status"] == "potential"


async def test_create_customer_duplicate_phone(
    async_client: AsyncClient, auth_headers, test_user, db_session
):
    """POST /api/v1/customers returns 400 when phone already exists."""
    await async_client.post("/api/v1/customers", headers=auth_headers, json={
        "name": "张三",
        "phone": "13900002222",
    })

    resp = await async_client.post("/api/v1/customers", headers=auth_headers, json={
        "name": "李四",
        "phone": "13900002222",
    })
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "DUPLICATE_PHONE"


async def test_list_customers(
    async_client: AsyncClient, auth_headers, test_user
):
    """GET /api/v1/customers returns paginated customer list."""
    # Create two customers
    for i in range(2):
        await async_client.post("/api/v1/customers", headers=auth_headers, json={
            "name": f"客户{i}",
            "phone": f"1390000333{i}",
        })

    resp = await async_client.get("/api/v1/customers", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 2
    assert len(body["items"]) >= 2


async def test_get_customer_detail(
    async_client: AsyncClient, auth_headers, test_user
):
    """GET /api/v1/customers/{id} returns customer detail with follow_ups."""
    create_resp = await async_client.post("/api/v1/customers", headers=auth_headers, json={
        "name": "王五",
        "phone": "13900004444",
    })
    customer_id = create_resp.json()["id"]

    resp = await async_client.get(f"/api/v1/customers/{customer_id}", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "王五"
    assert "follow_ups" in body


async def test_update_customer(
    async_client: AsyncClient, auth_headers, test_user, db_session
):
    """PUT /api/v1/customers/{id} updates customer fields."""
    create_resp = await async_client.post("/api/v1/customers", headers=auth_headers, json={
        "name": "赵六",
        "phone": "13900005555",
    })
    customer_id = create_resp.json()["id"]

    # Fetch the customer to get a valid version timestamp
    result = await db_session.execute(select(Customer).where(Customer.id == customer_id))
    customer = result.scalar_one()
    version = int(customer.created_at.timestamp())

    resp = await async_client.put(
        f"/api/v1/customers/{customer_id}",
        headers=auth_headers,
        json={"name": "赵六六", "version": version},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "赵六六"


async def test_add_follow_up(
    async_client: AsyncClient, auth_headers, test_user
):
    """POST /api/v1/customers/{id}/follow-ups adds a follow-up record."""
    create_resp = await async_client.post("/api/v1/customers", headers=auth_headers, json={
        "name": "孙七",
        "phone": "13900006666",
    })
    customer_id = create_resp.json()["id"]

    resp = await async_client.post(
        f"/api/v1/customers/{customer_id}/follow-ups",
        headers=auth_headers,
        json={"type": "phone", "content": "电话回访，客户有意向"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["content"] == "电话回访，客户有意向"
    assert body["type"] == "phone"


async def test_transfer_customer(
    async_client: AsyncClient, auth_headers, test_user, test_sale_user
):
    """POST /api/v1/customers/{id}/transfer reassigns the customer."""
    create_resp = await async_client.post("/api/v1/customers", headers=auth_headers, json={
        "name": "周八",
        "phone": "13900007777",
        "assigned_sale_id": test_user.id,
    })
    customer_id = create_resp.json()["id"]

    resp = await async_client.post(
        f"/api/v1/customers/{customer_id}/transfer",
        headers=auth_headers,
        json={"target_sale_id": test_sale_user.id},
    )
    assert resp.status_code == 200
    assert resp.json()["assigned_sale_id"] == test_sale_user.id


async def test_recycle_customer(
    async_client: AsyncClient, auth_headers, test_user
):
    """POST /api/v1/customers/{id}/recycle puts customer back into pool."""
    create_resp = await async_client.post("/api/v1/customers", headers=auth_headers, json={
        "name": "吴九",
        "phone": "13900008888",
        "assigned_sale_id": test_user.id,
    })
    customer_id = create_resp.json()["id"]

    resp = await async_client.post(
        f"/api/v1/customers/{customer_id}/recycle",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["assigned_sale_id"] is None
    assert resp.json()["recycled_at"] is not None


async def test_customer_pool_list(
    async_client: AsyncClient, auth_headers, test_user
):
    """GET /api/v1/customer-pool lists unassigned customers."""
    # Create and recycle a customer
    create_resp = await async_client.post("/api/v1/customers", headers=auth_headers, json={
        "name": "郑十",
        "phone": "13900009999",
        "assigned_sale_id": test_user.id,
    })
    customer_id = create_resp.json()["id"]
    await async_client.post(
        f"/api/v1/customers/{customer_id}/recycle", headers=auth_headers
    )

    resp = await async_client.get("/api/v1/customer-pool", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1


async def test_claim_from_pool(
    async_client: AsyncClient, auth_headers, test_user
):
    """POST /api/v1/customer-pool/{id}/claim assigns the customer to current user."""
    # Create and recycle a customer
    create_resp = await async_client.post("/api/v1/customers", headers=auth_headers, json={
        "name": "钱十一",
        "phone": "13900010000",
        "assigned_sale_id": test_user.id,
    })
    customer_id = create_resp.json()["id"]
    await async_client.post(
        f"/api/v1/customers/{customer_id}/recycle", headers=auth_headers
    )

    resp = await async_client.post(
        f"/api/v1/customer-pool/{customer_id}/claim",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["assigned_sale_id"] == test_user.id
    assert body["status"] == "following"
