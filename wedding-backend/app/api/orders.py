from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.order import OrderStatus
from app.middleware.auth import get_current_user
from app.models.user import User
from app.middleware.logging import log_operation
from app.schemas.order import OrderCreate, OrderUpdate, StatusTransition, PaymentCreate
from app.services.order_service import OrderService, order_to_dict, payment_to_dict, contract_to_dict

router = APIRouter()


# ── Routes ───────────────────────────────────────────────────────────────────

@router.get("")
async def list_orders(
    status: Optional[OrderStatus] = Query(None),
    sale_id: Optional[int] = Query(None),
    planner_id: Optional[int] = Query(None),
    keyword: Optional[str] = Query(None),
    date_start: Optional[date] = Query(None),
    date_end: Optional[date] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = OrderService(db)
    return await service.list_orders(
        status=status,
        sale_id=sale_id,
        planner_id=planner_id,
        keyword=keyword,
        date_start=date_start,
        date_end=date_end,
        page=page,
        page_size=page_size,
    )


@router.get("/{order_id}")
async def get_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = OrderService(db)
    return await service.get_order_detail(order_id)


@router.post("")
async def create_order(
    body: OrderCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = OrderService(db)
    order = await service.create_order(body, user.id)
    await log_operation(db, user.id, request, {"order_id": order.id, "order_no": order.order_no})
    return order_to_dict(order)


@router.put("/{order_id}")
async def update_order(
    order_id: int,
    body: OrderUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = OrderService(db)
    order = await service.update_order(order_id, body)
    update_data = body.model_dump(exclude_unset=True)
    await log_operation(db, user.id, request, {"order_id": order_id, "updated_fields": list(update_data.keys())})
    return order_to_dict(order)


@router.put("/{order_id}/status")
async def transition_status(
    order_id: int,
    body: StatusTransition,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = OrderService(db)
    order = await service.transition_status(order_id, body.status)
    await log_operation(db, user.id, request, {
        "order_id": order_id,
        "status_from": body.status.value,
        "status_to": body.status.value,
    })
    return order_to_dict(order)


@router.post("/{order_id}/payments")
async def record_payment(
    order_id: int,
    body: PaymentCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = OrderService(db)
    payment = await service.record_payment(order_id, body)
    await log_operation(db, user.id, request, {"order_id": order_id, "payment_id": payment.id, "amount": body.amount})
    return payment_to_dict(payment)


@router.post("/{order_id}/contract")
async def upload_contract(
    order_id: int,
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = OrderService(db)
    content = await file.read()
    contract = await service.upload_contract(order_id, content, file.filename)
    await log_operation(db, user.id, request, {"order_id": order_id, "contract_id": contract.id})
    return contract_to_dict(contract)


@router.get("/{order_id}/quote-pdf")
async def generate_quote_pdf(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = OrderService(db)
    return await service.generate_quote_pdf(order_id)
