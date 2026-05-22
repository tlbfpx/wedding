from app.events import event_bus, DomainEvent
from app.events.event_types import APPROVAL_APPROVED


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


def register_event_handlers():
    event_bus.subscribe(APPROVAL_APPROVED, on_approval_approved)
