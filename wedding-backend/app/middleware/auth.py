from __future__ import annotations
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User, Role
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


async def get_current_user_with_permissions(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(select(Role).where(Role.id == user.role_id))
    role = result.scalar_one_or_none()
    permissions = json.loads(role.permissions) if role else {}
    return {"user": user, "permissions": permissions}


def require_permission(module: str, action: str):
    async def checker(ctx: dict = Depends(get_current_user_with_permissions)):
        perms = ctx["permissions"]
        module_perms = perms.get(module, {})
        scope = module_perms.get(action, "none")
        if scope == "none":
            raise HTTPException(status_code=403, detail="Insufficient permission")
        ctx["scope"] = scope
        return ctx
    return checker
