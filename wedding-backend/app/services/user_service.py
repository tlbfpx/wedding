from __future__ import annotations

from datetime import date, datetime
from typing import Optional

import bcrypt
import json
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, Role, OperationLog
from app.models.user import TeamEnum, UserStatus
from app.schemas.user import UserCreate, UserUpdate, RoleUpdate
from app.utils.errors import AppException
from app.utils.pagination import PageResponse


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


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_users(
        self,
        team: Optional[TeamEnum] = None,
        status: Optional[UserStatus] = None,
        keyword: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PageResponse:
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

        total_result = await self.db.execute(select(func.count()).select_from(query.subquery()))
        total = total_result.scalar_one()

        offset = (page - 1) * page_size
        query = query.order_by(User.created_at.desc()).offset(offset).limit(page_size)
        result = await self.db.execute(query)
        users = result.scalars().all()

        return PageResponse(
            items=[_user_to_dict(u) for u in users],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=(total + page_size - 1) // page_size,
        )

    async def create_user(self, data: UserCreate) -> dict:
        existing = await self.db.execute(select(User).where(User.username == data.username))
        if existing.scalar_one_or_none():
            raise AppException(400, "DUPLICATE_USERNAME", "用户名已存在")

        role_result = await self.db.execute(select(Role).where(Role.id == data.role_id))
        if not role_result.scalar_one_or_none():
            raise AppException(400, "INVALID_ROLE", "角色不存在")

        password_hash = bcrypt.hashpw(data.password.encode(), bcrypt.gensalt()).decode()

        new_user = User(
            username=data.username,
            password_hash=password_hash,
            name=data.name,
            phone=data.phone,
            role_id=data.role_id,
            team=data.team,
            status=UserStatus.active,
        )
        self.db.add(new_user)
        await self.db.commit()
        await self.db.refresh(new_user)
        return _user_to_dict(new_user)

    async def update_user(self, user_id: int, data: UserUpdate) -> dict:
        result = await self.db.execute(select(User).where(User.id == user_id))
        target = result.scalar_one_or_none()
        if not target:
            raise AppException(404, "NOT_FOUND", "用户不存在")

        update_data = data.model_dump(exclude_unset=True, exclude={"password"})

        if data.role_id is not None:
            role_result = await self.db.execute(select(Role).where(Role.id == data.role_id))
            if not role_result.scalar_one_or_none():
                raise AppException(400, "INVALID_ROLE", "角色不存在")

        for key, value in update_data.items():
            setattr(target, key, value)

        if data.password:
            target.password_hash = bcrypt.hashpw(data.password.encode(), bcrypt.gensalt()).decode()

        await self.db.commit()
        await self.db.refresh(target)
        return _user_to_dict(target)

    async def list_roles(self) -> list[dict]:
        result = await self.db.execute(select(Role).order_by(Role.id))
        roles = result.scalars().all()
        return [_role_to_dict(r) for r in roles]

    async def update_role(self, role_id: int, data: RoleUpdate) -> dict:
        result = await self.db.execute(select(Role).where(Role.id == role_id))
        role = result.scalar_one_or_none()
        if not role:
            raise AppException(404, "NOT_FOUND", "角色不存在")

        if data.name is not None:
            role.name = data.name
        if data.permissions is not None:
            role.permissions = json.dumps(data.permissions, ensure_ascii=False)

        await self.db.commit()
        await self.db.refresh(role)
        return _role_to_dict(role)

    async def list_operation_logs(
        self,
        user_id: Optional[int] = None,
        module: Optional[str] = None,
        action: Optional[str] = None,
        date_start: Optional[date] = None,
        date_end: Optional[date] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PageResponse:
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

        total_result = await self.db.execute(select(func.count()).select_from(query.subquery()))
        total = total_result.scalar_one()

        offset = (page - 1) * page_size
        query = query.order_by(OperationLog.created_at.desc()).offset(offset).limit(page_size)
        result = await self.db.execute(query)
        logs = result.scalars().all()

        # Build user name lookup
        log_user_ids = list(set(l.user_id for l in logs))
        user_map: dict[int, str] = {}
        if log_user_ids:
            uresult = await self.db.execute(select(User).where(User.id.in_(log_user_ids)))
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
