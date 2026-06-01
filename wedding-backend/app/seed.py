from __future__ import annotations
import asyncio
import json
import bcrypt
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session, engine
from app.models import Base, Role, User, CustomerSource
from app.models.user import TeamEnum, UserStatus


ROLES = [
    {
        "name": "管理员",
        "permissions": {
            "crm": {"read": "all", "write": "all"},
            "schedule": {"read": "all", "write": "all"},
            "order": {"read": "all", "write": "all"},
            "supplier": {"read": "all", "write": "all"},
            "dashboard": {"read": "all"},
            "report": {"read": "all"},
            "system": {"read": "all", "write": "all"},
            "finance": {"read": "all", "write": "all", "approve": "all", "export": "all"},
        },
    },
    {
        "name": "销售主管",
        "permissions": {
            "crm": {"read": "all", "write": "all"},
            "schedule": {"read": "all", "write": "none"},
            "order": {"read": "all", "write": "all"},
            "supplier": {"read": "all", "write": "none"},
            "dashboard": {"read": "team"},
            "report": {"read": "all"},
            "system": {"read": "none", "write": "none"},
            "finance": {"read": "all", "write": "all"},
        },
    },
    {
        "name": "销售",
        "permissions": {
            "crm": {"read": "own", "write": "own"},
            "schedule": {"read": "all", "write": "none"},
            "order": {"read": "own", "write": "own"},
            "supplier": {"read": "none", "write": "none"},
            "dashboard": {"read": "none"},
            "report": {"read": "none"},
            "system": {"read": "none", "write": "none"},
        },
    },
    {
        "name": "策划主管",
        "permissions": {
            "crm": {"read": "all", "write": "none"},
            "schedule": {"read": "all", "write": "all"},
            "order": {"read": "all", "write": "none"},
            "supplier": {"read": "all", "write": "none"},
            "dashboard": {"read": "team"},
            "report": {"read": "all"},
            "system": {"read": "none", "write": "none"},
        },
    },
    {
        "name": "策划师",
        "permissions": {
            "crm": {"read": "all", "write": "none"},
            "schedule": {"read": "own", "write": "own"},
            "order": {"read": "all", "write": "none"},
            "supplier": {"read": "all", "write": "none"},
            "dashboard": {"read": "none"},
            "report": {"read": "none"},
            "system": {"read": "none", "write": "none"},
        },
    },
    {
        "name": "设计主管",
        "permissions": {
            "crm": {"read": "none", "write": "none"},
            "schedule": {"read": "all", "write": "none"},
            "order": {"read": "all", "write": "none"},
            "supplier": {"read": "all", "write": "none"},
            "dashboard": {"read": "team"},
            "report": {"read": "none"},
            "system": {"read": "none", "write": "none"},
        },
    },
    {
        "name": "设计师",
        "permissions": {
            "crm": {"read": "none", "write": "none"},
            "schedule": {"read": "all", "write": "none"},
            "order": {"read": "none", "write": "none"},
            "supplier": {"read": "none", "write": "none"},
            "dashboard": {"read": "none"},
            "report": {"read": "none"},
            "system": {"read": "none", "write": "none"},
        },
    },
]

CUSTOMER_SOURCES = ["线上咨询", "转介绍", "线下门店", "小红书", "抖音", "其他"]

ADMIN_USER = {
    "username": "admin",
    "password": "admin123",
    "name": "管理员",
    "role_id": 1,
    "team": TeamEnum.management,
}


async def seed_roles(session: AsyncSession) -> None:
    existing_count = await session.scalar(select(func.count()).select_from(Role))
    if existing_count and existing_count > 0:
        print(f"[skip] Roles already seeded ({existing_count} found)")
        return

    for role_data in ROLES:
        role = Role(
            name=role_data["name"],
            permissions=json.dumps(role_data["permissions"], ensure_ascii=False),
        )
        session.add(role)

    await session.flush()
    print(f"[ok] Seeded {len(ROLES)} roles")


async def seed_admin(session: AsyncSession) -> None:
    existing = await session.scalar(
        select(User).where(User.username == ADMIN_USER["username"])
    )
    if existing:
        print(f"[skip] Admin user '{ADMIN_USER['username']}' already exists")
        return

    password_hash = bcrypt.hashpw(
        ADMIN_USER["password"].encode("utf-8"), bcrypt.gensalt()
    ).decode("utf-8")

    admin = User(
        username=ADMIN_USER["username"],
        password_hash=password_hash,
        name=ADMIN_USER["name"],
        role_id=ADMIN_USER["role_id"],
        team=ADMIN_USER["team"],
        status=UserStatus.active,
    )
    session.add(admin)
    await session.flush()
    print(f"[ok] Seeded admin user '{ADMIN_USER['username']}'")


async def seed_customer_sources(session: AsyncSession) -> None:
    existing_count = await session.scalar(
        select(func.count()).select_from(CustomerSource)
    )
    if existing_count and existing_count > 0:
        print(f"[skip] Customer sources already seeded ({existing_count} found)")
        return

    for name in CUSTOMER_SOURCES:
        source = CustomerSource(name=name)
        session.add(source)

    await session.flush()
    print(f"[ok] Seeded {len(CUSTOMER_SOURCES)} customer sources")


async def main() -> None:
    print("Creating tables if not exist...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("[ok] Tables ready")

    async with async_session() as session:
        async with session.begin():
            await seed_roles(session)
            await seed_admin(session)
            await seed_customer_sources(session)

    print("Seed completed successfully.")


if __name__ == "__main__":
    asyncio.run(main())
