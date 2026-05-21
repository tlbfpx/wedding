import os
from datetime import datetime, date
from typing import Optional
from decimal import Decimal
from io import BytesIO

from fastapi import APIRouter, Depends, Query, Request, UploadFile, File
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.database import get_db
from app.models import Order, OrderItem, Payment, Contract
from app.models.order import OrderStatus, ItemType, PaymentMethod, PaymentStatus, ContractStatus
from app.middleware.auth import get_current_user
from app.models.user import User
from app.utils.errors import AppException
from app.utils.pagination import PageResponse
from app.middleware.logging import log_operation
from app.config import settings

router = APIRouter()

VALID_TRANSITIONS = {
    OrderStatus.intention: [OrderStatus.signed, OrderStatus.cancelled],
    OrderStatus.signed: [OrderStatus.executing, OrderStatus.cancelled],
    OrderStatus.executing: [OrderStatus.completed, OrderStatus.cancelled],
    OrderStatus.completed: [],
    OrderStatus.cancelled: [],
}


# ── Schemas ──────────────────────────────────────────────────────────────────

class OrderItemInput(BaseModel):
    type: ItemType
    name: str
    quantity: int = 1
    unit_price: float
    supplier_id: Optional[int] = None
    note: Optional[str] = None


class OrderCreate(BaseModel):
    customer_id: int
    planner_id: Optional[int] = None
    sale_id: int
    discount: Optional[float] = 1.00
    note: Optional[str] = None
    items: list[OrderItemInput]


class OrderUpdate(BaseModel):
    note: Optional[str] = None
    discount: Optional[float] = None
    planner_id: Optional[int] = None


class StatusTransition(BaseModel):
    status: OrderStatus


class PaymentCreate(BaseModel):
    amount: float
    method: PaymentMethod
    note: Optional[str] = None


# ── Routes ───────────────────────────────────────────────────────────────────

@router.get("/")
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
    query = select(Order)

    if status:
        query = query.where(Order.status == status)
    if sale_id:
        query = query.where(Order.sale_id == sale_id)
    if planner_id:
        query = query.where(Order.planner_id == planner_id)
    if keyword:
        query = query.where(
            (Order.order_no.like(f"%{keyword}%")) | (Order.note.like(f"%{keyword}%"))
        )
    if date_start:
        query = query.where(Order.created_at >= datetime.combine(date_start, datetime.min.time()))
    if date_end:
        query = query.where(Order.created_at <= datetime.combine(date_end, datetime.max.time()))

    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar_one()

    offset = (page - 1) * page_size
    query = query.order_by(Order.created_at.desc()).offset(offset).limit(page_size)
    result = await db.execute(query)
    orders = result.scalars().all()

    return PageResponse(
        items=[_order_to_dict(o) for o in orders],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/{order_id}")
async def get_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise AppException(404, "NOT_FOUND", "订单不存在")

    items_result = await db.execute(
        select(OrderItem).where(OrderItem.order_id == order_id)
    )
    items = items_result.scalars().all()

    payments_result = await db.execute(
        select(Payment).where(Payment.order_id == order_id).order_by(Payment.created_at.desc())
    )
    payments = payments_result.scalars().all()

    contract_result = await db.execute(
        select(Contract).where(Contract.order_id == order_id)
    )
    contract = contract_result.scalar_one_or_none()

    return {
        **_order_to_dict(order),
        "items": [_item_to_dict(i) for i in items],
        "payments": [_payment_to_dict(p) for p in payments],
        "contract": _contract_to_dict(contract) if contract else None,
    }


@router.post("/")
async def create_order(
    body: OrderCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    order_no = await _generate_order_no(db)

    total_amount = Decimal("0")
    order_items = []
    for item_input in body.items:
        amount = Decimal(str(item_input.unit_price)) * item_input.quantity
        total_amount += amount
        order_items.append(
            OrderItem(
                type=item_input.type,
                name=item_input.name,
                quantity=item_input.quantity,
                unit_price=item_input.unit_price,
                amount=float(amount),
                supplier_id=item_input.supplier_id,
                note=item_input.note,
            )
        )

    total_amount = total_amount * Decimal(str(body.discount or 1.0))

    order = Order(
        order_no=order_no,
        customer_id=body.customer_id,
        planner_id=body.planner_id,
        sale_id=body.sale_id,
        status=OrderStatus.intention,
        total_amount=float(total_amount),
        paid_amount=0,
        discount=body.discount or 1.00,
        note=body.note,
    )
    db.add(order)
    await db.flush()

    for item in order_items:
        item.order_id = order.id
        db.add(item)

    await db.commit()
    await db.refresh(order)

    await log_operation(db, user.id, request, {"order_id": order.id, "order_no": order_no})
    return _order_to_dict(order)


@router.put("/{order_id}")
async def update_order(
    order_id: int,
    body: OrderUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise AppException(404, "NOT_FOUND", "订单不存在")

    if order.status != OrderStatus.intention:
        raise AppException(400, "INVALID_STATUS", "仅意向状态的订单可修改")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(order, key, value)

    await db.commit()
    await db.refresh(order)

    await log_operation(db, user.id, request, {"order_id": order_id, "updated_fields": list(update_data.keys())})
    return _order_to_dict(order)


@router.put("/{order_id}/status")
async def transition_status(
    order_id: int,
    body: StatusTransition,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise AppException(404, "NOT_FOUND", "订单不存在")

    allowed = VALID_TRANSITIONS.get(order.status, [])
    if body.status not in allowed:
        raise AppException(
            400,
            "INVALID_TRANSITION",
            f"订单状态 {order.status.value} 不能转换为 {body.status.value}",
        )

    old_status = order.status.value
    order.status = body.status
    await db.commit()
    await db.refresh(order)

    await log_operation(db, user.id, request, {
        "order_id": order_id,
        "status_from": old_status,
        "status_to": body.status.value,
    })
    return _order_to_dict(order)


@router.post("/{order_id}/payments")
async def record_payment(
    order_id: int,
    body: PaymentCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise AppException(404, "NOT_FOUND", "订单不存在")

    new_paid = Decimal(str(order.paid_amount)) + Decimal(str(body.amount))
    total = Decimal(str(order.total_amount))
    if new_paid > total:
        raise AppException(400, "PAYMENT_EXCEEDS_TOTAL", "付款金额超过订单总额")

    payment = Payment(
        order_id=order_id,
        amount=body.amount,
        method=body.method,
        status=PaymentStatus.confirmed,
        paid_at=datetime.utcnow(),
        note=body.note,
    )
    db.add(payment)

    order.paid_amount = float(new_paid)
    await db.commit()
    await db.refresh(payment)

    await log_operation(db, user.id, request, {"order_id": order_id, "payment_id": payment.id, "amount": body.amount})
    return _payment_to_dict(payment)


@router.post("/{order_id}/contract")
async def upload_contract(
    order_id: int,
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise AppException(404, "NOT_FOUND", "订单不存在")

    file_size = 0
    content = await file.read()
    file_size = len(content)
    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    if file_size > max_bytes:
        raise AppException(400, "FILE_TOO_LARGE", f"文件大小不能超过{settings.MAX_FILE_SIZE_MB}MB")

    upload_dir = os.path.join(settings.UPLOAD_DIR, "contracts")
    os.makedirs(upload_dir, exist_ok=True)
    file_name = f"{order_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{file.filename}"
    file_path = os.path.join(upload_dir, file_name)

    with open(file_path, "wb") as f:
        f.write(content)

    file_url = f"/uploads/contracts/{file_name}"

    existing_result = await db.execute(
        select(Contract).where(Contract.order_id == order_id)
    )
    contract = existing_result.scalar_one_or_none()

    if contract:
        contract.file_url = file_url
        contract.status = ContractStatus.pending
        contract.signed_at = None
    else:
        contract = Contract(
            order_id=order_id,
            file_url=file_url,
            status=ContractStatus.pending,
        )
        db.add(contract)

    await db.commit()
    await db.refresh(contract)

    await log_operation(db, user.id, request, {"order_id": order_id, "contract_id": contract.id})
    return _contract_to_dict(contract)


@router.get("/{order_id}/quote-pdf")
async def generate_quote_pdf(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from fastapi.responses import StreamingResponse

    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise AppException(404, "NOT_FOUND", "订单不存在")

    items_result = await db.execute(
        select(OrderItem).where(OrderItem.order_id == order_id)
    )
    items = items_result.scalars().all()

    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas as pdf_canvas

    buffer = BytesIO()
    c = pdf_canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 18)
    c.drawString(30 * mm, height - 20 * mm, f"Wedding Order Quote - {order.order_no}")

    c.setFont("Helvetica", 11)
    y = height - 35 * mm
    c.drawString(30 * mm, y, f"Customer ID: {order.customer_id}")
    y -= 8 * mm
    c.drawString(30 * mm, y, f"Status: {order.status.value}")
    y -= 8 * mm
    c.drawString(30 * mm, y, f"Date: {order.created_at.strftime('%Y-%m-%d') if order.created_at else 'N/A'}")

    y -= 15 * mm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(30 * mm, y, "Items")
    c.setFont("Helvetica", 10)
    y -= 8 * mm

    for item in items:
        c.drawString(30 * mm, y, f"{item.name} x{item.quantity} @ {float(item.unit_price):.2f} = {float(item.amount):.2f}")
        y -= 7 * mm

    y -= 5 * mm
    c.setFont("Helvetica-Bold", 12)
    discount_label = f"Discount: {float(order.discount):.2f}"
    total_label = f"Total: {float(order.total_amount):.2f}"
    paid_label = f"Paid: {float(order.paid_amount):.2f}"
    c.drawString(30 * mm, y, discount_label)
    y -= 8 * mm
    c.drawString(30 * mm, y, total_label)
    y -= 8 * mm
    c.drawString(30 * mm, y, paid_label)

    c.showPage()
    c.save()
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename=quote_{order.order_no}.pdf"},
    )


# ── Helpers ──────────────────────────────────────────────────────────────────

async def _generate_order_no(db: AsyncSession) -> str:
    today_str = datetime.utcnow().strftime("%Y%m%d")
    prefix = f"WD{today_str}"

    result = await db.execute(
        select(func.count()).select_from(Order).where(Order.order_no.like(f"{prefix}%"))
    )
    count = result.scalar_one()

    seq = str(count + 1).zfill(3)
    return f"{prefix}{seq}"


def _order_to_dict(o: Order) -> dict:
    return {
        "id": o.id,
        "order_no": o.order_no,
        "customer_id": o.customer_id,
        "planner_id": o.planner_id,
        "sale_id": o.sale_id,
        "status": o.status.value,
        "total_amount": float(o.total_amount),
        "paid_amount": float(o.paid_amount),
        "discount": float(o.discount),
        "note": o.note,
        "created_at": o.created_at.isoformat() if o.created_at else None,
        "updated_at": o.updated_at.isoformat() if o.updated_at else None,
    }


def _item_to_dict(i: OrderItem) -> dict:
    return {
        "id": i.id,
        "order_id": i.order_id,
        "type": i.type.value,
        "name": i.name,
        "quantity": i.quantity,
        "unit_price": float(i.unit_price),
        "amount": float(i.amount),
        "supplier_id": i.supplier_id,
        "note": i.note,
    }


def _payment_to_dict(p: Payment) -> dict:
    return {
        "id": p.id,
        "order_id": p.order_id,
        "amount": float(p.amount),
        "method": p.method.value,
        "status": p.status.value,
        "paid_at": p.paid_at.isoformat() if p.paid_at else None,
        "note": p.note,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }


def _contract_to_dict(c: Contract) -> dict:
    return {
        "id": c.id,
        "order_id": c.order_id,
        "file_url": c.file_url,
        "status": c.status.value,
        "signed_at": c.signed_at.isoformat() if c.signed_at else None,
    }
