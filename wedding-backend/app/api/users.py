from __future__ import annotations
from datetime import date, datetime
from typing import Optional

import bcrypt
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
import json

from app.database import get_db
from app.models import User, Role, OperationLog
from app.models.user import TeamEnum, UserStatus
from app.middleware.auth import get_current_user
from app.utils.errors import AppException
from app.utils.pagination import PageResponse
from app.middleware.logging import log_operation

router = APIRouter()


# ── Schemas ──────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    username: str
    password: str
    name: str
    phone: Optional[str] = None
    role_id: int
    team: TeamEnum


class UserUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    role_id: Optional[int] = None
    team: Optional[TeamEnum] = None
    status: Optional[UserStatus] = None
    password: Optional[str] = None


class RoleUpdate(BaseModel):
    name: Optional[str] = None
    permissions: Optional[list[str]] = None


# ── User Routes ──────────────────────────────────────────────────────────────

@router.get("")
async def list_users(
    team: Optional[TeamEnum] = Query(None),
    status: Optional[UserStatus] = Query(None),
    keyword: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = select(User)

    if team:
        query = query.where(User.team == team)
    if status:
        query = query.where(User.status == status)
    if keyword:
        query = query.where(
            (User.name.like(f"%{keyword}%"))
            | (User.username.like(f"%{keyword}%"))
            | (User.phone.like(f"%{keyword}%"))
        )

    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar_one()

    offset = (page - 1) * page_size
    query = query.order_by(User.created_at.desc()).offset(offset).limit(page_size)
    result = await db.execute(query)
    users = result.scalars().all()

    return PageResponse(
        items=[_user_to_dict(u) for u in users],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.post("")
async def create_user(
    body: UserCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    existing = await db.execute(select(User).where(User.username == body.username))
    if existing.scalar_one_or_none():
        raise AppException(400, "DUPLICATE_USERNAME", "用户名已存在")

    role_result = await db.execute(select(Role).where(Role.id == body.role_id))
    if not role_result.scalar_one_or_none():
        raise AppException(400, "INVALID_ROLE", "角色不存在")

    password_hash = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode()

    new_user = User(
        username=body.username,
        password_hash=password_hash,
        name=body.name,
        phone=body.phone,
        role_id=body.role_id,
        team=body.team,
        status=UserStatus.active,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    await log_operation(db, user.id, request, {"user_id": new_user.id, "username": body.username})
    return _user_to_dict(new_user)


@router.put("/{user_id}")
async def update_user(
    user_id: int,
    body: UserUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(User).where(User.id == user_id))
    target = result.scalar_one_or_none()
    if not target:
        raise AppException(404, "NOT_FOUND", "用户不存在")

    update_data = body.model_dump(exclude_unset=True, exclude={"password"})

    if body.role_id is not None:
        role_result = await db.execute(select(Role).where(Role.id == body.role_id))
        if not role_result.scalar_one_or_none():
            raise AppException(400, "INVALID_ROLE", "角色不存在")

    for key, value in update_data.items():
        setattr(target, key, value)

    if body.password:
        target.password_hash = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode()

    await db.commit()
    await db.refresh(target)

    await log_operation(db, user.id, request, {"target_user_id": user_id, "updated_fields": list(update_data.keys())})
    return _user_to_dict(target)


# ── Role Routes ──────────────────────────────────────────────────────────────

@router.get("/roles")
async def list_roles(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Role).order_by(Role.id))
    roles = result.scalars().all()
    return [_role_to_dict(r) for r in roles]


@router.put("/roles/{role_id}")
async def update_role(
    role_id: int,
    body: RoleUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()
    if not role:
        raise AppException(404, "NOT_FOUND", "角色不存在")

    if body.name is not None:
        role.name = body.name
    if body.permissions is not None:
        role.permissions = json.dumps(body.permissions, ensure_ascii=False)

    await db.commit()
    await db.refresh(role)

    await log_operation(db, user.id, request, {"role_id": role_id})
    return _role_to_dict(role)


# ── Operation Log Routes ─────────────────────────────────────────────────────

@router.get("/operation-logs")
async def list_operation_logs(
    user_id: Optional[int] = Query(None),
    module: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    date_start: Optional[date] = Query(None),
    date_end: Optional[date] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = select(OperationLog)

    if user_id:
        query = query.where(OperationLog.user_id == user_id)
    if module:
        query = query.where(OperationLog.module == module)
    if action:
        query = query.where(OperationLog.action == action)
    if date_start:
        query = query.where(OperationLog.created_at >= datetime.combine(date_start, datetime.min.time()))
    if date_end:
        query = query.where(OperationLog.created_at <= datetime.combine(date_end, datetime.max.time()))

    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar_one()

    offset = (page - 1) * page_size
    query = query.order_by(OperationLog.created_at.desc()).offset(offset).limit(page_size)
    result = await db.execute(query)
    logs = result.scalars().all()

    # Build user name lookup
    user_ids = list(set(l.user_id for l in logs))
    user_map = {}
    if user_ids:
        uresult = await db.execute(select(User).where(User.id.in_(user_ids)))
        for u in uresult.scalars().all():
            user_map[u.id] = u.name

    return PageResponse(
        items=[_log_to_dict(l, user_map) for l in logs],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


# ── Helpers ──────────────────────────────────────────────────────────────────

def _user_to_dict(u: User) -> dict:
    return {
        "id": u.id,
        "username": u.username,
        "name": u.name,
        "phone": u.phone,
        "role_id": u.role_id,
        "team": u.team.value,
        "status": u.status.value,
        "created_at": u.created_at.isoformat() if u.created_at else None,
        "updated_at": u.updated_at.isoformat() if u.updated_at else None,
    }


_MODULE_KEY_MAP = {
    "crm": "customers",
    "schedule": "events",
    "event": "events",
    "order": "orders",
    "supplier": "suppliers",
    "venue": "venues",
    "user": "users",
    "staff": "users",
    "role": "roles",
    "finance": "finance",
    "report": "reports",
    "system": "system",
}


def _role_to_dict(r: Role) -> dict:
    perms = r.permissions
    if isinstance(perms, str):
        try:
            perms = json.loads(perms)
        except (json.JSONDecodeError, TypeError):
            perms = []
    if isinstance(perms, dict):
        result = []
        for module, actions in perms.items():
            mapped = _MODULE_KEY_MAP.get(module, module)
            if isinstance(actions, dict):
                for action, scope in actions.items():
                    if scope != "none":
                        result.append(f"{mapped}:{action}")
            else:
                result.append(f"{mapped}:{actions}")
        perms = result
    if isinstance(perms, list):
        perms = [
            f"{_MODULE_KEY_MAP.get(p.split(':')[0], p.split(':')[0])}:{p.split(':', 1)[1]}"
            if ':' in p else p
            for p in perms
        ]
    return {
        "id": r.id,
        "name": r.name,
        "display_name": r.name,
        "permissions": perms if isinstance(perms, list) else [],
    }


def _log_to_dict(l: OperationLog, user_map: dict = None) -> dict:
    return {
        "id": l.id,
        "user_id": l.user_id,
        "user_name": (user_map or {}).get(l.user_id),
        "module": l.module,
        "action": l.action,
        "target": l.target,
        "detail": l.detail,
        "ip": l.ip,
        "created_at": l.created_at.isoformat() if l.created_at else None,
    }
