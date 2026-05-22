from app.events import event_bus, DomainEvent
from app.events.event_types import (
    APPROVAL_APPROVED,
    APPROVAL_CREATED,
    APPROVAL_RESOLVED,
    EVENT_CREATED,
    EVENT_UPDATED,
)


async def on_approval_approved(event: DomainEvent, context: dict = None):
    from app.services.order_service import OrderService
    from app.models.order import ApprovalType

    approval_type = event.payload["approval_type"]
    target_id = event.payload["target_id"]

    # Use the same db session from the publisher for transactional consistency
    db = context["db"] if context else None
    if db is None:
        return

    service = OrderService(db)
    if approval_type == ApprovalType.cancel.value:
        await service.cancel_order(target_id)
    elif approval_type == ApprovalType.refund.value:
        await service.refund_order(target_id)
    # Note: db.commit() is not called here because the caller
    # (ApprovalService.decide_approval) manages the transaction.


async def on_approval_created(event: DomainEvent, context: dict = None):
    """Notify approvers when a new approval is created."""
    from sqlalchemy import select
    from app.models.user import User, TeamEnum, UserStatus
    from app.services.notification_service import NotificationService

    db = context["db"] if context else None
    if db is None:
        return

    approval_id = event.payload.get("approval_id")
    approval_type = event.payload.get("approval_type")
    applicant_id = event.payload.get("applicant_id")
    applicant_name = event.payload.get("applicant_name", "未知用户")

    # Query active management users (admins/managers)
    result = await db.execute(
        select(User).where(
            User.team == TeamEnum.management,
            User.status == UserStatus.active,
        )
    )
    managers = result.scalars().all()

    service = NotificationService(db)
    type_label = {
        "discount": "折扣审批",
        "refund": "退款审批",
        "cancel": "取消审批",
    }.get(approval_type, "审批")

    for manager in managers:
        await service.create_notification(
            user_id=manager.id,
            title=f"新{type_label}申请",
            content=f"{applicant_name} 提交了一份{type_label}申请（编号: {approval_id}），请及时处理。",
            type="approval",
            related_id=approval_id,
            related_type="approval",
        )


async def on_approval_resolved(event: DomainEvent, context: dict = None):
    """Notify the applicant when approval is resolved."""
    from app.services.notification_service import NotificationService

    db = context["db"] if context else None
    if db is None:
        return

    approval_id = event.payload.get("approval_id")
    approval_type = event.payload.get("approval_type")
    status = event.payload.get("status")
    approver_name = event.payload.get("approver_name", "审批人")
    applicant_id = event.payload.get("applicant_id")

    if not applicant_id:
        return

    service = NotificationService(db)
    type_label = {
        "discount": "折扣审批",
        "refund": "退款审批",
        "cancel": "取消审批",
    }.get(approval_type, "审批")

    status_label = "已通过" if status == "approved" else "已驳回"

    await service.create_notification(
        user_id=applicant_id,
        title=f"{type_label}{status_label}",
        content=f"您提交的{type_label}申请（编号: {approval_id}）已被 {approver_name} {status_label}。",
        type="approval",
        related_id=approval_id,
        related_type="approval",
    )


async def on_event_created(event: DomainEvent, context: dict = None):
    """Notify related sale when a schedule event is created."""
    from app.services.notification_service import NotificationService

    db = context["db"] if context else None
    if db is None:
        return

    event_id = event.payload.get("event_id")
    event_title = event.payload.get("event_title", "活动")
    order_id = event.payload.get("order_id")
    planner_name = event.payload.get("planner_name", "策划师")
    sale_id = event.payload.get("sale_id")

    if not sale_id:
        return

    service = NotificationService(db)
    await service.create_notification(
        user_id=sale_id,
        title=f"新活动安排: {event_title}",
        content=f"策划师 {planner_name} 已为订单（编号: {order_id}）创建了活动安排「{event_title}」。",
        type="schedule",
        related_id=event_id,
        related_type="event",
    )


async def on_event_updated(event: DomainEvent, context: dict = None):
    """Notify related sale and planner when a schedule event is updated."""
    from app.services.notification_service import NotificationService

    db = context["db"] if context else None
    if db is None:
        return

    event_id = event.payload.get("event_id")
    event_title = event.payload.get("event_title", "活动")
    order_id = event.payload.get("order_id")
    planner_name = event.payload.get("planner_name", "策划师")
    sale_id = event.payload.get("sale_id")
    planner_id = event.payload.get("planner_id")

    service = NotificationService(db)

    notified_ids = set()
    if sale_id:
        await service.create_notification(
            user_id=sale_id,
            title=f"活动更新: {event_title}",
            content=f"策划师 {planner_name} 更新了订单（编号: {order_id}）的活动安排「{event_title}」。",
            type="schedule",
            related_id=event_id,
            related_type="event",
        )
        notified_ids.add(sale_id)

    if planner_id and planner_id not in notified_ids:
        await service.create_notification(
            user_id=planner_id,
            title=f"活动更新: {event_title}",
            content=f"活动安排「{event_title}」（订单编号: {order_id}）已更新。",
            type="schedule",
            related_id=event_id,
            related_type="event",
        )


def register_event_handlers():
    event_bus.subscribe(APPROVAL_APPROVED, on_approval_approved)
    event_bus.subscribe(APPROVAL_CREATED, on_approval_created)
    event_bus.subscribe(APPROVAL_RESOLVED, on_approval_resolved)
    event_bus.subscribe(EVENT_CREATED, on_event_created)
    event_bus.subscribe(EVENT_UPDATED, on_event_updated)
