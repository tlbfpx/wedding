from __future__ import annotations
from typing import Optional

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.utils.auth import decode_token
from app.utils.cache import redis_client
import json

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    token = credentials.credentials

    is_blacklisted = await redis_client.get(f"jwt:blacklist:{token}")
    if is_blacklisted:
        raise HTTPException(status_code=401, detail="Token has been revoked")

    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    result = await db.execute(select(User).where(User.id == int(user_id), User.status == "active"))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user


async def _get_permissions(user: User, db: AsyncSession) -> dict:
    """Load permissions from cache or DB."""
    cache_key = f"role:perms:{user.role_id}"
    cached = await redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    from app.models.user import Role
    result = await db.execute(select(Role).where(Role.id == user.role_id))
    role = result.scalar_one_or_none()
    permissions = json.loads(role.permissions) if role else {}
    await redis_client.setex(cache_key, 300, json.dumps(permissions, ensure_ascii=False))
    return permissions


async def get_permissions_ctx(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    permissions = await _get_permissions(user, db)
    return {"user": user, "permissions": permissions}


# Keep backward compat alias
get_current_user_with_permissions = get_permissions_ctx


def require_permission(module: str, action: str):
    """Decorator that checks user has permission for module:action.

    Returns context dict with keys: user, permissions, scope.
    Admin (role_id=1) bypasses all checks with scope='all'.
    """
    async def checker(ctx: dict = Depends(get_permissions_ctx)):
        user = ctx["user"]
        perms = ctx["permissions"]

        # Admin bypass: check if all module permissions have full access
        system_perm = perms.get("system")
        if isinstance(system_perm, dict) and system_perm.get("write") == "all":
            ctx["scope"] = "all"
            return ctx

        module_perms = perms.get(module, {})

        # Handle boolean permission (e.g. "system": true/false)
        if isinstance(module_perms, bool):
            if not module_perms:
                raise HTTPException(status_code=403, detail="Insufficient permission")
            ctx["scope"] = "all"
            return ctx

        # Handle string permission (e.g. "dashboard": "all"/"team"/"none")
        if isinstance(module_perms, str):
            if module_perms == "none":
                raise HTTPException(status_code=403, detail="Insufficient permission")
            ctx["scope"] = module_perms
            return ctx

        # Handle dict permission (e.g. {"read": "all", "write": "own"})
        if isinstance(module_perms, dict):
            scope = module_perms.get(action, "none")
            if scope == "none":
                raise HTTPException(status_code=403, detail="Insufficient permission")
            ctx["scope"] = scope
            return ctx

        raise HTTPException(status_code=403, detail="Insufficient permission")
    return checker
