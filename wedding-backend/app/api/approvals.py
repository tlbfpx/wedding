from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.order import ApprovalType, ApprovalStatus
from app.middleware.auth import require_permission
from app.middleware.logging import log_operation
from app.schemas.approval import ApprovalCreate, ApprovalDecision
from app.services.approval_service import ApprovalService, approval_to_dict

router = APIRouter()


@router.get("")
async def list_approvals(
    status: Optional[ApprovalStatus] = Query(None),
    type: Optional[ApprovalType] = Query(None),
    applicant_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(require_permission("order", "read")),
):
    service = ApprovalService(db)
    return await service.list_approvals(
        status=status,
        type=type,
        applicant_id=applicant_id,
        page=page,
        page_size=page_size,
    )


@router.post("")
async def create_approval(
    body: ApprovalCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(require_permission("order", "write")),
):
    service = ApprovalService(db)
    user = ctx["user"]
    approval = await service.create_approval(body, user.id)
    await log_operation(db, user.id, request, {"approval_id": approval.id, "type": body.type.value})
    return approval_to_dict(approval, {user.id: user})


@router.put("/{approval_id}")
async def decide_approval(
    approval_id: int,
    body: ApprovalDecision,
    request: Request,
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(require_permission("order", "write")),
):
    service = ApprovalService(db)
    user = ctx["user"]
    approval = await service.decide_approval(approval_id, body, user.id)
    await log_operation(db, user.id, request, {
        "approval_id": approval_id,
        "decision": body.status.value,
    })
    return approval_to_dict(approval, {user.id: user})
