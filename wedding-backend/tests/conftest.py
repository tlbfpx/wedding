from __future__ import annotations
"""
Shared pytest fixtures for the wedding management system test suite.

Uses an in-memory SQLite database via aiosqlite for async testing,
and mocks Redis to avoid requiring a live Redis server.
"""

import asyncio
from datetime import datetime
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event as sa_event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models import (
    User, Role, OperationLog,
    Customer, FollowUp, CustomerSource,
    Supplier, SupplierService, SupplierEvaluation,
    Order, OrderItem, Payment, Contract, Approval,
    Event, EventResource, StaffSchedule, Venue,
    Notification,
)
from app.models.user import TeamEnum, UserStatus
from app.utils.auth import create_access_token, create_refresh_token
from app.main import app
from app.database import get_db
from app.utils import cache as cache_module
from app.events.handlers import register_event_handlers


# ---------------------------------------------------------------------------
# Patch models that reference created_at/updated_at in their _to_dict helpers
# but don't inherit from TimestampMixin.  We add the columns to the __table__
# so that the SQLite test schema has them.
# ---------------------------------------------------------------------------
from sqlalchemy import Column, DateTime


def _ensure_timestamp_columns(model_cls):
    """Add created_at / updated_at columns to a model if missing."""
    if not hasattr(model_cls, "__table__"):
        return
    table = model_cls.__table__
    if "created_at" not in table.c:
        col = Column("created_at", DateTime, default=datetime.utcnow)
        table.append_column(col)
        setattr(model_cls, "created_at", col)
    if "updated_at" not in table.c:
        col = Column("updated_at", DateTime, nullable=True, onupdate=datetime.utcnow)
        table.append_column(col)
        setattr(model_cls, "updated_at", col)


for _cls in (Supplier, SupplierService, Event, EventResource, Venue, Contract):
    _ensure_timestamp_columns(_cls)


# ---------------------------------------------------------------------------
# SQLite async engine for testing
# ---------------------------------------------------------------------------
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(
    bind=test_engine, class_=AsyncSession, expire_on_commit=False
)


# Auto-set timestamps on before_flush for models that need them
from sqlalchemy.orm import Session as SyncSession

@sa_event.listens_for(SyncSession, "before_flush")
def _set_test_timestamps(session, flush_context, instances):
    new_ids = {id(obj) for obj in session.new}
    for obj in session.new:
        if hasattr(obj, "created_at") and getattr(obj, "created_at", None) is None:
            obj.created_at = datetime.utcnow()
    for obj in session.dirty:
        # Skip objects that are also in session.new to avoid setting updated_at on insert
        if id(obj) in new_ids:
            continue
        if hasattr(obj, "updated_at"):
            obj.updated_at = datetime.utcnow()


# ---------------------------------------------------------------------------
# Mock Redis client
# ---------------------------------------------------------------------------
class MockRedis:
    """In-memory fake Redis client that supports the subset of commands used."""

    def __init__(self):
        self._store: dict[str, str] = {}
        self._expiry: dict[str, int] = {}

    async def get(self, key: str) -> str | None:
        return self._store.get(key)

    async def set(self, key: str, value: str, **kwargs) -> None:
        self._store[key] = value

    async def setex(self, key: str, ttl: int, value: str) -> None:
        self._store[key] = value
        self._expiry[key] = ttl

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)

    async def incr(self, key: str) -> int:
        current = int(self._store.get(key, "0"))
        current += 1
        self._store[key] = str(current)
        return current

    async def expire(self, key: str, ttl: int) -> None:
        self._expiry[key] = ttl

    async def exists(self, key: str) -> int:
        """Check if key exists (1=yes, 0=no)."""
        return 1 if key in self._store else 0

    async def ping(self) -> bool:
        """Redis ping (for health checks)."""
        return True

    async def keys(self, pattern: str = "*") -> list[str]:
        return list(self._store.keys())

    async def flushdb(self) -> None:
        self._store.clear()
        self._expiry.clear()


mock_redis = MockRedis()


# ---------------------------------------------------------------------------
# Override dependencies
# ---------------------------------------------------------------------------

async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        yield session


def override_redis():
    """Return the mock Redis instance."""
    return mock_redis


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database():
    """Create all tables once per test session."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(autouse=True)
async def clean_tables(setup_database):
    """Truncate all tables between tests to keep isolation."""
    async with test_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())
    # Also clear mock redis between tests
    await mock_redis.flushdb()
    # Reset rate limiter to avoid test interference
    from app.middleware.global_rate_limit import _global_limiter
    _global_limiter.reset()


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a test database session."""
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def async_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Provide an httpx AsyncClient wired to the FastAPI app with overridden
    dependencies for database and Redis.
    """
    # Register event handlers (httpx ASGITransport does not trigger FastAPI
    # startup events, so we must do this explicitly).
    register_event_handlers()

    # Override database dependency
    app.dependency_overrides[get_db] = override_get_db

    # Override redis_client module-level reference
    original_redis = cache_module.redis_client
    cache_module.redis_client = mock_redis

    # Also override in middleware.auth since it imports redis_client
    from app.middleware import auth as auth_middleware
    original_middleware_redis = auth_middleware.redis_client
    auth_middleware.redis_client = mock_redis

    # Override in api.auth as well
    from app.api import auth as auth_api
    original_auth_api_redis = auth_api.redis_client
    auth_api.redis_client = mock_redis

    # Override in api.dashboard
    from app.api import dashboard as dashboard_api
    original_dashboard_redis = dashboard_api.redis_client
    dashboard_api.redis_client = mock_redis

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://testserver", follow_redirects=True
    ) as client:
        yield client

    # Restore original redis references
    cache_module.redis_client = original_redis
    auth_middleware.redis_client = original_middleware_redis
    auth_api.redis_client = original_auth_api_redis
    dashboard_api.redis_client = original_dashboard_redis

    # Clear dependency overrides
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_role(db_session: AsyncSession) -> Role:
    """Create a default admin role with full permissions."""
    role = Role(
        name="管理员",
        permissions='{"crm": {"read": "all", "write": "all"}, '
                    '"order": {"read": "all", "write": "all"}, '
                    '"supplier": {"read": "all", "write": "all"}, '
                    '"schedule": {"read": "all", "write": "all"}, '
                    '"dashboard": {"read": "all"}, '
                    '"report": {"read": "all"}, '
                    '"system": {"read": "all", "write": "all"}, '
                    '"finance": {"read": "all", "write": "all", "approve": "all", "export": "all"}}',
    )
    db_session.add(role)
    await db_session.commit()
    await db_session.refresh(role)
    return role


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession, test_role: Role) -> User:
    """Create a test admin user."""
    import bcrypt
    password_hash = bcrypt.hashpw("testpass123".encode(), bcrypt.gensalt()).decode()
    user = User(
        username="admin",
        password_hash=password_hash,
        name="Test Admin",
        phone="13800000000",
        role_id=test_role.id,
        team=TeamEnum.management,
        status=UserStatus.active,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_sale_user(db_session: AsyncSession, test_role: Role) -> User:
    """Create a test sales user with limited permissions."""
    import bcrypt
    password_hash = bcrypt.hashpw("salepass123".encode(), bcrypt.gensalt()).decode()
    role = Role(
        name="销售",
        permissions='{"crm": {"read": "own", "write": "own"}, '
                    '"order": {"read": "own", "write": "own"}, '
                    '"schedule": {"read": "all", "write": "none"}, '
                    '"supplier": {"read": "none", "write": "none"}, '
                    '"dashboard": {"read": "none"}, '
                    '"report": {"read": "none"}, '
                    '"system": {"read": "none", "write": "none"}}',
    )
    db_session.add(role)
    await db_session.commit()
    await db_session.refresh(role)

    user = User(
        username="sale1",
        password_hash=password_hash,
        name="Test Sale",
        phone="13800000001",
        role_id=role.id,
        team=TeamEnum.sales,
        status=UserStatus.active,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def auth_headers(test_user: User) -> dict[str, str]:
    """Return authorization headers with a valid JWT for the test admin user."""
    token = create_access_token({"sub": str(test_user.id)})
    return {"Authorization": f"Bearer {token}", "X-CSRF-Token": "test-csrf-token-for-integration-tests"}


@pytest_asyncio.fixture
async def sale_auth_headers(test_sale_user: User) -> dict[str, str]:
    """Return authorization headers with a valid JWT for the test sale user."""
    token = create_access_token({"sub": str(test_sale_user.id)})
    return {"Authorization": f"Bearer {token}", "X-CSRF-Token": "test-csrf-token-for-integration-tests"}
