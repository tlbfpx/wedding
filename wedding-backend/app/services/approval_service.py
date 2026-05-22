from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Approval, Order
from app.models.order import ApprovalType, ApprovalStatus
from app.models.user import User
from app.schemas.approval import ApprovalCreate, ApprovalDecision
from app.utils.errors import AppException
from app.utils.pagination import PageResponse
from app.events import event_bus, DomainEvent
from app.events.event_types import APPROVAL_APPROVED


class ApprovalService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_approvals(
        self,
        status: Optional[ApprovalStatus] = None,
        type: Optional[ApprovalType] = None,
        applicant_id: Optional[int] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PageResponse:
        query = select(Approval)

        if status:
            query = query.where(Approval.status == status)
        if type:
            query = query.where(Approval.type == type)
        if applicant_id:
            query = query.where(Approval.applicant_id == applicant_id)

        total_result = await self.db.execute(select(func.count()).select_from(query.subquery()))
        total = total_result.scalar_one()

        offset = (page - 1) * page_size
        query = query.order_by(Approval.created_at.desc()).offset(offset).limit(page_size)
        result = await self.db.execute(query)
        approvals = result.scalars().all()

        # Build user lookup for applicant/approver names
        user_ids = set()
        order_ids = set()
        for a in approvals:
            user_ids.add(a.applicant_id)
            if a.approver_id:
                user_ids.add(a.approver_id)
            order_ids.add(a.target_id)

        user_map = {}
        if user_ids:
            uresult = await self.db.execute(select(User).where(User.id.in_(user_ids)))
            for u in uresult.scalars().all():
                user_map[u.id] = u

        order_map = {}
        if order_ids:
            oresult = await self.db.execute(select(Order).where(Order.id.in_(order_ids)))
            for o in oresult.scalars().all():
                order_map[o.id] = o

        return PageResponse(
            items=[approval_to_dict(a, user_map, order_map) for a in approvals],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=(total + page_size - 1) // page_size,
        )

    async def create_approval(self, data: ApprovalCreate, user_id: int) -> Approval:
        approval = Approval(
            type=data.type,
            target_id=data.target_id,
            applicant_id=user_id,
            reason=data.reason,
        )
        self.db.add(approval)
        await self.db.commit()
        await self.db.refresh(approval)
        return approval

    async def decide_approval(
        self, approval_id: int, decision: ApprovalDecision, user_id: int
    ) -> Approval:
        result = await self.db.execute(select(Approval).where(Approval.id == approval_id))
        approval = result.scalar_one_or_none()
        if not approval:
            raise AppException(404, "NOT_FOUND", "审批记录不存在")

        if approval.status != ApprovalStatus.pending:
            raise AppException(400, "ALREADY_RESOLVED", "该审批已处理")

        if decision.status == ApprovalStatus.pending:
            raise AppException(400, "INVALID_STATUS", "不能将审批状态设置为待审")

        approval.status = decision.status
        approval.approver_id = user_id
        approval.note = decision.note
        approval.resolved_at = datetime.utcnow()

        if decision.status == ApprovalStatus.approved:
            await event_bus.publish(
                DomainEvent(
                    event_type=APPROVAL_APPROVED,
                    payload={
                        "approval_id": approval.id,
                        "approval_type": approval.type.value,
                        "target_id": approval.target_id,
                        "approver_id": user_id,
                    },
                ),
                context={"db": self.db},
            )

        await self.db.commit()
        await self.db.refresh(approval)
        return approval


# ── Serialization helpers ────────────────────────────────────────────────────

def approval_to_dict(a: Approval, user_map: dict = None, order_map: dict = None) -> dict:
    applicant = None
    if user_map and a.applicant_id in user_map:
        u = user_map[a.applicant_id]
        applicant = {"id": u.id, "name": u.name}

    approver = None
    if user_map and a.approver_id and a.approver_id in user_map:
        u = user_map[a.approver_id]
        approver = {"id": u.id, "name": u.name}

    order_no = None
    if order_map and a.target_id in order_map:
        order_no = order_map[a.target_id].order_no

    return {
        "id": a.id,
        "type": a.type.value,
        "target_id": a.target_id,
        "order_id": a.target_id,
        "order_no": order_no,
        "applicant_id": a.applicant_id,
        "applicant": applicant,
        "approver_id": a.approver_id,
        "approver": approver,
        "status": a.status.value,
        "reason": a.reason,
        "approver_remark": a.note,
        "resolved_at": a.resolved_at.isoformat() if a.resolved_at else None,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }
