"""Tests for RBAC permission enforcement."""
from __future__ import annotations

import bcrypt
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, Role, TeamEnum, UserStatus
from app.utils.auth import create_access_token
from app.main import app
from app.database import get_db
from app.utils import cache as cache_module
from app.events.handlers import register_event_handlers
from tests.conftest import MockRedis, override_get_db, mock_redis


@pytest_asyncio.fixture
async def restricted_role(db_session: AsyncSession) -> Role:
    """Role with no permissions."""
    role = Role(
        name="无权限",
        permissions='{"crm": {"read": "none", "write": "none"}, '
                    '"order": {"read": "none", "write": "none"}, '
                    '"supplier": {"read": "none", "write": "none"}, '
                    '"schedule": {"read": "none", "write": "none"}, '
                    '"dashboard": {"read": "none"}, '
                    '"report": {"read": "none"}, '
                    '"system": {"read": "none", "write": "none"}}',
    )
    db_session.add(role)
    await db_session.commit()
    await db_session.refresh(role)
    return role


@pytest_asyncio.fixture
async def restricted_user(db_session: AsyncSession, restricted_role: Role) -> User:
    """User with no permissions (non-admin)."""
    password_hash = bcrypt.hashpw("nopass123".encode(), bcrypt.gensalt()).decode()
    user = User(
        username="noperm",
        password_hash=password_hash,
        name="No Permission",
        phone="13800000999",
        role_id=restricted_role.id,
        team=TeamEnum.sales,
        status=UserStatus.active,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def restricted_auth_headers(restricted_user: User) -> dict[str, str]:
    token = create_access_token({"sub": str(restricted_user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def rbac_client(db_session: AsyncSession) -> AsyncClient:
    """Client wired for RBAC testing."""
    register_event_handlers()
    app.dependency_overrides[get_db] = override_get_db

    original_redis = cache_module.redis_client
    cache_module.redis_client = mock_redis

    from app.middleware import auth as auth_middleware
    original_middleware_redis = auth_middleware.redis_client
    auth_middleware.redis_client = mock_redis

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

    cache_module.redis_client = original_redis
    auth_middleware.redis_client = original_middleware_redis
    app.dependency_overrides.clear()


# ── Permission denied tests ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_rbac_customer_list_denied(rbac_client: AsyncClient, restricted_auth_headers: dict, db_session: AsyncSession):
    resp = await rbac_client.get("/api/v1/customers", headers=restricted_auth_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_rbac_customer_create_denied(rbac_client: AsyncClient, restricted_auth_headers: dict):
    resp = await rbac_client.post("/api/v1/customers", headers=restricted_auth_headers, json={
        "name": "Test", "phone": "13800001111", "gender": "male",
    })
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_rbac_order_list_denied(rbac_client: AsyncClient, restricted_auth_headers: dict):
    resp = await rbac_client.get("/api/v1/orders", headers=restricted_auth_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_rbac_supplier_list_denied(rbac_client: AsyncClient, restricted_auth_headers: dict):
    resp = await rbac_client.get("/api/v1/suppliers", headers=restricted_auth_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_rbac_event_list_denied(rbac_client: AsyncClient, restricted_auth_headers: dict):
    resp = await rbac_client.get("/api/v1/events", headers=restricted_auth_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_rbac_dashboard_denied(rbac_client: AsyncClient, restricted_auth_headers: dict):
    resp = await rbac_client.get("/api/v1/dashboard/overview", headers=restricted_auth_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_rbac_report_denied(rbac_client: AsyncClient, restricted_auth_headers: dict):
    resp = await rbac_client.get("/api/v1/reports/export?report_type=order", headers=restricted_auth_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_rbac_user_list_denied(rbac_client: AsyncClient, restricted_auth_headers: dict):
    resp = await rbac_client.get("/api/v1/users", headers=restricted_auth_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_rbac_import_denied(rbac_client: AsyncClient, restricted_auth_headers: dict):
    resp = await rbac_client.get("/api/v1/imports/template?import_type=customer", headers=restricted_auth_headers)
    assert resp.status_code == 403


# ── Admin bypass tests ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_rbac_admin_bypass_customer_list(rbac_client: AsyncClient, auth_headers: dict):
    """Admin (role_id=1) should bypass all permission checks."""
    resp = await rbac_client.get("/api/v1/customers", headers=auth_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_rbac_admin_bypass_dashboard(rbac_client: AsyncClient, auth_headers: dict):
    resp = await rbac_client.get("/api/v1/dashboard/overview", headers=auth_headers)
    assert resp.status_code == 200


# ── Scope filtering tests ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_rbac_sale_user_sees_own_customers(
    rbac_client: AsyncClient, sale_auth_headers: dict, db_session: AsyncSession, test_sale_user: User
):
    """Sale user with 'own' scope should be able to list customers."""
    # Create a customer assigned to this sale user
    from app.models.customer import Customer, CustomerStatus, Gender
    customer = Customer(
        name="Test Customer",
        phone="13800002222",
        gender=Gender.male,
        status=CustomerStatus.following,
        assigned_sale_id=test_sale_user.id,
    )
    db_session.add(customer)
    await db_session.commit()

    resp = await rbac_client.get("/api/v1/customers", headers=sale_auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    # Should only see their own customers (or none if scope filtering works)
    for item in data.get("items", []):
        assert item["assigned_sale_id"] == test_sale_user.id


# ── Notifications accessible to all authenticated users ─────────────────────

@pytest.mark.asyncio
async def test_rbac_notifications_accessible(rbac_client: AsyncClient, restricted_auth_headers: dict):
    """Notifications use get_current_user, not require_permission."""
    resp = await rbac_client.get("/api/v1/notifications", headers=restricted_auth_headers)
    assert resp.status_code == 200
