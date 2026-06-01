"""
退款服务
"""
from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.finance.infrastructure.repositories import RefundRepository, ReceivableRepository, TransactionRepository
from app.finance.domain.entities import Refund, Receivable
from app.finance.domain.entities.enums import RefundStatus, TransactionType, ExpenseCategory
from app.events import DomainEvent, event_bus
from app.events.event_types import APPROVAL_CREATED
from app.utils.errors import AppException


class RefundService:
    """退款服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.refund_repo = RefundRepository(db)
        self.receivable_repo = ReceivableRepository(db)
        self.transaction_repo = TransactionRepository(db)

    async def request_refund(
        self,
        order_id: int,
        amount: float,
        reason: str,
        user_id: int,
        note: Optional[str] = None,
    ) -> Refund:
        """申请退款

        Args:
            order_id: 订单ID
            amount: 退款金额
            reason: 退款原因
            user_id: 申请人ID
            note: 备注

        Returns:
            Refund: 退款记录

        Raises:
            AppException: 退款金额超过订单已付金额
        """
        # 校验金额
        from app.models.order import Order

        order_result = await self.db.execute(
            select(Order).where(Order.id == order_id)
        )
        order = order_result.scalar_one_or_none()
        if not order:
            raise AppException(404, "ORDER_NOT_FOUND", "订单不存在")

        if Decimal(str(amount)) > Decimal(str(order.paid_amount)):
            raise AppException(400, "REFUND_EXCEEDS_PAID", "退款金额超过订单已付金额")

        # 创建退款记录
        refund = await self.refund_repo.create(
            order_id=order_id,
            amount=amount,
            reason=reason,
            created_by=user_id,
            note=note,
        )

        # 创建审批记录
        from app.models.order import Approval, ApprovalStatus, ApprovalType

        approval = Approval(
            type=ApprovalType.refund,
            target_id=refund.id,
            applicant_id=user_id,
            reason=reason,
            status=ApprovalStatus.pending,
        )
        self.db.add(approval)
        await self.db.flush()

        refund.approval_id = approval.id
        await self.refund_repo.update(refund)

        await self.db.commit()
        await self.db.refresh(refund)

        # 发布审批创建事件
        await event_bus.publish(DomainEvent(
            event_type=APPROVAL_CREATED,
            payload={
                "approval_id": approval.id,
                "approval_type": ApprovalType.refund.value,
                "target_id": refund.id,
                "applicant_id": user_id,
                "applicant_name": "",  # 由事件处理器填充
            }
        ))

        return refund

    async def handle_approval_approved(self, refund_id: int) -> Refund:
        """处理退款审批通过（由事件处理器调用）"""
        refund = await self.refund_repo.get(refund_id)
        if not refund or refund.status != RefundStatus.pending_approval:
            return refund

        # 更新退款状态
        refund.status = RefundStatus.approved
        refund.approved_at = datetime.utcnow()
        await self.refund_repo.update(refund)

        # 扣减订单已付金额
        from app.models.order import Order

        order_result = await self.db.execute(
            select(Order).where(Order.id == refund.order_id)
        )
        order = order_result.scalar_one_or_none()
        if order:
            order.paid_amount = float(Decimal(str(order.paid_amount)) - Decimal(str(refund.amount)))

            # 重新计算应收
            receivable = await self.receivable_repo.get_by_order(refund.order_id)
            if receivable:
                receivable.received_amount = Decimal(str(order.paid_amount))
                await self._update_receivable_status(receivable)
                await self.receivable_repo.update(receivable)

        # 发布退款批准事件
        from app.finance.domain.events.event_types import REFUND_APPROVED
        await event_bus.publish(DomainEvent(
            event_type=REFUND_APPROVED,
            payload={
                "refund_id": refund.id,
                "order_id": refund.order_id,
                "amount": str(refund.amount),
            }
        ))

        return refund

    async def handle_approval_rejected(self, refund_id: int, reason: str) -> Refund:
        """处理退款审批驳回（由事件处理器调用）"""
        refund = await self.refund_repo.get(refund_id)
        if not refund or refund.status != RefundStatus.pending_approval:
            return refund

        refund.status = RefundStatus.rejected
        await self.refund_repo.update(refund)

        # 发布退款拒绝事件
        from app.finance.domain.events.event_types import REFUND_REJECTED
        await event_bus.publish(DomainEvent(
            event_type=REFUND_REJECTED,
            payload={
                "refund_id": refund.id,
                "order_id": refund.order_id,
                "reason": reason,
            }
        ))

        return refund

    async def confirm_refund(self, refund_id: int) -> Refund:
        """确认退款（实际执行退款）"""
        refund = await self.refund_repo.get(refund_id)
        if not refund:
            raise AppException(404, "REFUND_NOT_FOUND", "退款记录不存在")

        if refund.status != RefundStatus.approved:
            raise AppException(400, "INVALID_STATUS", "退款状态不允许此操作")

        # 更新状态
        refund.status = RefundStatus.refunded
        refund.refunded_at = datetime.utcnow()
        await self.refund_repo.update(refund)

        # 创建退款支出明细
        await self.transaction_repo.create(
            type=TransactionType.expense,
            category=ExpenseCategory.refund,
            amount=Decimal(str(refund.amount)),
            order_id=refund.order_id,
            refund_id=refund.id,
            date=datetime.utcnow().date(),
            note=f"退款: {refund.reason}",
        )

        # 发布退款确认事件
        from app.finance.domain.events.event_types import REFUND_CONFIRMED
        await event_bus.publish(DomainEvent(
            event_type=REFUND_CONFIRMED,
            payload={
                "refund_id": refund.id,
                "order_id": refund.order_id,
                "amount": str(refund.amount),
            }
        ))

        return refund

    async def get_refund(self, refund_id: int) -> Refund:
        """获取退款记录"""
        refund = await self.refund_repo.get(refund_id)
        if not refund:
            raise AppException(404, "REFUND_NOT_FOUND", "退款记录不存在")
        return refund

    async def list_refunds(
        self,
        order_id: Optional[int] = None,
        status: Optional[RefundStatus] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Refund], int]:
        """查询退款列表"""
        offset = (page - 1) * page_size
        return await self.refund_repo.list(
            order_id=order_id,
            status=status,
            offset=offset,
            limit=page_size,
        )

    async def _update_receivable_status(self, receivable: Receivable) -> None:
        """更新应收状态"""
        from app.finance.application.services.receivable_service import ReceivableService

        service = ReceivableService(self.db)
        await service._update_receivable_status(receivable)
