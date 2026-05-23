from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
import bcrypt

from app.database import get_db
from app.models.user import User, Role
from app.utils.auth import create_access_token, create_refresh_token, decode_token
from app.utils.cache import redis_client
from app.middleware.auth import get_current_user, get_permissions_ctx
from app.config import settings
from app.middleware.rate_limit import limiter
import json

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/login", response_model=LoginResponse)
@limiter.limit("20/minute")
async def login(request: Request, req_body: LoginRequest, db: AsyncSession = Depends(get_db)):
    lock_key = f"login:fail:{req_body.username}"
    fail_count = await redis_client.get(lock_key)
    if fail_count and int(fail_count) >= 5:
        raise HTTPException(status_code=403, detail={"code": "ACCOUNT_LOCKED", "message": "账户已锁定，请30分钟后重试"})

    result = await db.execute(select(User).where(User.username == req_body.username, User.status == "active"))
    user = result.scalar_one_or_none()
    if not user or not bcrypt.checkpw(req_body.password.encode(), user.password_hash.encode()):
        await redis_client.incr(lock_key)
        await redis_client.expire(lock_key, 1800)
        raise HTTPException(status_code=401, detail={"code": "INVALID_CREDENTIALS", "message": "用户名或密码错误"})

    await redis_client.delete(lock_key)

    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})

    return LoginResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh")
async def refresh(req: RefreshRequest):
    payload = decode_token(req.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail={"code": "TOKEN_EXPIRED", "message": "刷新令牌无效或已过期"})

    access_token = create_access_token({"sub": payload["sub"]})
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/logout")
async def logout(user: User = Depends(get_current_user)):
    # Note: in production the token from the request would be passed here
    return {"message": "已登出"}


@router.get("/me")
async def me(ctx: dict = Depends(get_permissions_ctx)):
    user = ctx["user"]
    return {
        "id": user.id,
        "username": user.username,
        "name": user.name,
        "phone": user.phone,
        "team": user.team.value,
        "status": user.status.value,
        "permissions": ctx["permissions"],
    }
