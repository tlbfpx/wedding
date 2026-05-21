from datetime import datetime
from typing import Optional
from decimal import Decimal

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.database import get_db
from app.models import Approval, Order
from app.models.order import ApprovalType, ApprovalStatus, OrderStatus
from app.middleware.auth import get_current_user
from app.models.user import User
from app.utils.errors import AppException
from app.utils.pagination import PageResponse
from app.middleware.logging import log_operation

router = APIRouter()


# ── Schemas ──────────────────────────────────────────────────────────────────

class ApprovalCreate(BaseModel):
    type: ApprovalType
    target_id: int
    reason: str


class ApprovalDecision(BaseModel):
    status: ApprovalStatus
    note: Optional[str] = None


# ── Routes ───────────────────────────────────────────────────────────────────

@router.get("/")
async def list_approvals(
    status: Optional[ApprovalStatus] = Query(None),
    type: Optional[ApprovalType] = Query(None),
    applicant_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = select(Approval)

    if status:
        query = query.where(Approval.status == status)
    if type:
        query = query.where(Approval.type == type)
    if applicant_id:
        query = query.where(Approval.applicant_id == applicant_id)

    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar_one()

    offset = (page - 1) * page_size
    query = query.order_by(Approval.created_at.desc()).offset(offset).limit(page_size)
    result = await db.execute(query)
    approvals = result.scalars().all()

    return PageResponse(
        items=[_approval_to_dict(a) for a in approvals],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.post("/")
async def create_approval(
    body: ApprovalCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    approval = Approval(
        type=body.type,
        target_id=body.target_id,
        applicant_id=user.id,
        reason=body.reason,
    )
    db.add(approval)
    await db.commit()
    await db.refresh(approval)

    await log_operation(db, user.id, request, {"approval_id": approval.id, "type": body.type.value})
    return _approval_to_dict(approval)


@router.put("/{approval_id}")
async def decide_approval(
    approval_id: int,
    body: ApprovalDecision,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Approval).where(Approval.id == approval_id))
    approval = result.scalar_one_or_none()
    if not approval:
        raise AppException(404, "NOT_FOUND", "审批记录不存在")

    if approval.status != ApprovalStatus.pending:
        raise AppException(400, "ALREADY_RESOLVED", "该审批已处理")

    if body.status == ApprovalStatus.pending:
        raise AppException(400, "INVALID_STATUS", "不能将审批状态设置为待审")

    approval.status = body.status
    approval.approver_id = user.id
    approval.resolved_at = datetime.utcnow()

    # Execute associated action on approval
    if body.status == ApprovalStatus.approved:
        await _execute_approval_action(db, approval)

    await db.commit()
    await db.refresh(approval)

    await log_operation(db, user.id, request, {
        "approval_id": approval_id,
        "decision": body.status.value,
    })
    return _approval_to_dict(approval)


# ── Helpers ──────────────────────────────────────────────────────────────────

async def _execute_approval_action(db: AsyncSession, approval: Approval):
    if approval.type == ApprovalType.cancel:
        result = await db.execute(select(Order).where(Order.id == approval.target_id))
        order = result.scalar_one_or_none()
        if order:
            order.status = OrderStatus.cancelled

    elif approval.type == ApprovalType.discount:
        result = await db.execute(select(Order).where(Order.id == approval.target_id))
        order = result.scalar_one_or_none()
        if order:
            # Discount was already applied when the approval was requested;
            # marking approval confirms it, no further action needed.
            pass

    elif approval.type == ApprovalType.refund:
        result = await db.execute(select(Order).where(Order.id == approval.target_id))
        order = result.scalar_one_or_none()
        if order:
            order.paid_amount = 0


def _approval_to_dict(a: Approval) -> dict:
    return {
        "id": a.id,
        "type": a.type.value,
        "target_id": a.target_id,
        "applicant_id": a.applicant_id,
        "approver_id": a.approver_id,
        "status": a.status.value,
        "reason": a.reason,
        "resolved_at": a.resolved_at.isoformat() if a.resolved_at else None,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }
