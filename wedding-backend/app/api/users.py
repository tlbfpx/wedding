from __future__ import annotations
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import TeamEnum, UserStatus
from app.middleware.auth import get_current_user
from app.models.user import User
from app.middleware.logging import log_operation
from app.schemas.user import UserCreate, UserUpdate, RoleUpdate
from app.services.user_service import UserService

router = APIRouter()


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
    svc = UserService(db)
    return await svc.list_users(
        team=team,
        status=status,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )


@router.post("")
async def create_user(
    body: UserCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    svc = UserService(db)
    result = await svc.create_user(body)
    await log_operation(db, user.id, request, {"user_id": result["id"], "username": body.username})
    return result


@router.put("/{user_id}")
async def update_user(
    user_id: int,
    body: UserUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    svc = UserService(db)
    update_data = body.model_dump(exclude_unset=True, exclude={"password"})
    result = await svc.update_user(user_id, body)
    await log_operation(db, user.id, request, {"target_user_id": user_id, "updated_fields": list(update_data.keys())})
    return result


# ── Role Routes ──────────────────────────────────────────────────────────────

@router.get("/roles")
async def list_roles(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    svc = UserService(db)
    return await svc.list_roles()


@router.put("/roles/{role_id}")
async def update_role(
    role_id: int,
    body: RoleUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    svc = UserService(db)
    result = await svc.update_role(role_id, body)
    await log_operation(db, user.id, request, {"role_id": role_id})
    return result


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
    svc = UserService(db)
    return await svc.list_operation_logs(
        user_id=user_id,
        module=module,
        action=action,
        date_start=date_start,
        date_end=date_end,
        page=page,
        page_size=page_size,
    )
