"""
财务管理模块事件处理器

处理来自其他模块的事件，以及本模块发布的事件
"""

from typing import Optional
from datetime import datetime, date, timedelta
from decimal import Decimal

from app.events import DomainEvent, event_bus
from app.events.event_types import (
    ORDER_CREATED,
    ORDER_STATUS_CHANGED,
    ORDER_CANCELLED,
    APPROVAL_APPROVED,
    APPROVAL_REJECTED,
)
from app.utils.errors import AppException


async def on_order_created(event: DomainEvent, context: dict = None):
    """
    订单创建时自动生成应收记录

    Payload: {order_id, total_amount, customer_id, sale_id}
    """
    db = context.get("db") if context else None
    if not db:
        return

    order_id = event.payload.get("order_id")
    total_amount = Decimal(str(event.payload.get("total_amount", 0)))

    if not order_id:
        return

    # 延迟导入避免循环依赖
    from app.finance.infrastructure.repositories.receivable_repository import ReceivableRepository
    from app.finance.domain.entities.enums import ReceivableStatus

    repo = ReceivableRepository(db)

    # 检查是否已存在应收
    existing = await repo.get_by_order(order_id)
    if existing:
        return

    # 创建应收记录
    receivable = await repo.create(
        order_id=order_id,
        total_amount=total_amount,
        received_amount=Decimal("0"),
        status=ReceivableStatus.unpaid,
        due_date=None,  # 签约时设置
    )

    # 发布应收创建事件
    from app.finance.domain.events.event_types import RECEIVABLE_CREATED
    await event_bus.publish(DomainEvent(
        event_type=RECEIVABLE_CREATED,
        payload={
            "receivable_id": receivable.id,
            "order_id": order_id,
            "total_amount": str(total_amount),
        }
    ))


async def on_order_status_changed(event: DomainEvent, context: dict = None):
    """
    订单状态变更时更新应收

    Payload: {order_id, old_status, new_status}
    """
    db = context.get("db") if context else None
    if not db:
        return

    order_id = event.payload.get("order_id")
    new_status = event.payload.get("new_status")

    if not order_id or not new_status:
        return

    from app.finance.infrastructure.repositories.receivable_repository import ReceivableRepository
    from app.models.order import OrderStatus

    repo = ReceivableRepository(db)
    receivable = await repo.get_by_order(order_id)

    if not receivable:
        return

    # 签约时设置到期日（默认30天后）
    if new_status == OrderStatus.signed.value and not receivable.due_date:
        receivable.due_date = date.today() + timedelta(days=30)
        await repo.update(receivable)


async def on_order_cancelled(event: DomainEvent, context: dict = None):
    """
    订单取消时关闭关联应收、退款、开票

    Payload: {order_id}
    """
    db = context.get("db") if context else None
    if not db:
        return

    order_id = event.payload.get("order_id")
    if not order_id:
        return

    from app.finance.infrastructure.repositories.receivable_repository import ReceivableRepository
    from app.finance.domain.entities.enums import ReceivableStatus

    repo = ReceivableRepository(db)
    receivable = await repo.get_by_order(order_id)

    # 如果有未完成的应收，标记为已取消（或保留但不再追踪）
    # 这里选择保留记录，但不做额外处理
    # 实际业务可能需要根据需求调整


async def on_approval_approved(event: DomainEvent, context: dict = None):
    """
    审批通过时处理退款

    Payload: {approval_id, approval_type, target_id, approver_id}
    """
    db = context.get("db") if context else None
    if not db:
        return

    approval_type = event.payload.get("approval_type")
    target_id = event.payload.get("target_id")
    approver_id = event.payload.get("approver_id")

    if not approval_type or not target_id:
        return

    # 处理退款审批
    if approval_type == "refund":
        from app.finance.infrastructure.repositories.refund_repository import RefundRepository
        from app.finance.domain.entities.enums import RefundStatus
        from app.finance.infrastructure.repositories.receivable_repository import ReceivableRepository

        refund_repo = RefundRepository(db)
        receivable_repo = ReceivableRepository(db)

        refund = await refund_repo.get(target_id)
        if not refund or refund.status != RefundStatus.pending_approval:
            return

        # 更新退款状态
        refund.status = RefundStatus.approved
        refund.approved_by = approver_id
        refund.approved_at = datetime.utcnow()
        await refund_repo.update(refund)

        # 扣减订单已付金额
        from sqlalchemy import select
        from app.models.order import Order

        order_result = await db.execute(select(Order).where(Order.id == refund.order_id))
        order = order_result.scalar_one_or_none()
        if order:
            order.paid_amount = float(Decimal(str(order.paid_amount)) - Decimal(str(refund.amount)))

            # 重新计算应收
            receivable = await receivable_repo.get_by_order(refund.order_id)
            if receivable:
                receivable.received_amount = Decimal(str(order.paid_amount))
                await _update_receivable_status(receivable)
                await receivable_repo.update(receivable)

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


async def on_approval_rejected(event: DomainEvent, context: dict = None):
    """
    审批驳回时更新退款状态

    Payload: {approval_id, approval_type, target_id, reason}
    """
    db = context.get("db") if context else None
    if not db:
        return

    approval_type = event.payload.get("approval_type")
    target_id = event.payload.get("target_id")

    if not approval_type or not target_id:
        return

    # 处理退款审批驳回
    if approval_type == "refund":
        from app.finance.infrastructure.repositories.refund_repository import RefundRepository
        from app.finance.domain.entities.enums import RefundStatus

        refund_repo = RefundRepository(db)
        refund = await refund_repo.get(target_id)

        if refund and refund.status == RefundStatus.pending_approval:
            refund.status = RefundStatus.rejected
            await refund_repo.update(refund)

            # 发布退款拒绝事件
            from app.finance.domain.events.event_types import REFUND_REJECTED
            await event_bus.publish(DomainEvent(
                event_type=REFUND_REJECTED,
                payload={
                    "refund_id": refund.id,
                    "order_id": refund.order_id,
                    "reason": event.payload.get("reason", ""),
                }
            ))


async def _update_receivable_status(receivable) -> None:
    """更新应收状态（根据已收金额计算）"""
    from app.finance.domain.entities.enums import ReceivableStatus

    if receivable.received_amount <= 0:
        receivable.status = ReceivableStatus.unpaid
    elif receivable.received_amount < receivable.total_amount:
        receivable.status = ReceivableStatus.partial
    else:
        # 已全额收款
        if receivable.due_date and date.today() > receivable.due_date:
            # 即使逾期，但已全额收款也算 paid
            receivable.status = ReceivableStatus.paid
        else:
            receivable.status = ReceivableStatus.paid

    # 检查逾期
    if receivable.due_date and date.today() > receivable.due_date:
        if receivable.received_amount < receivable.total_amount:
            receivable.status = ReceivableStatus.overdue
            receivable.overdue_days = (date.today() - receivable.due_date).days
    else:
        receivable.overdue_days = 0


def register_finance_event_handlers():
    """
    注册财务管理模块的所有事件处理器

    在应用启动时调用此函数
    """
    event_bus.subscribe(ORDER_CREATED, on_order_created)
    event_bus.subscribe(ORDER_STATUS_CHANGED, on_order_status_changed)
    event_bus.subscribe(ORDER_CANCELLED, on_order_cancelled)
    event_bus.subscribe(APPROVAL_APPROVED, on_approval_approved)
    event_bus.subscribe(APPROVAL_REJECTED, on_approval_rejected)
