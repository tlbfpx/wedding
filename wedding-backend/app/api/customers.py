from datetime import datetime, date
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.models import Customer, FollowUp, CustomerSource
from app.models.customer import CustomerStatus, Gender, FollowUpType
from app.middleware.auth import get_current_user
from app.models.user import User
from app.utils.errors import AppException
from app.utils.pagination import PageParams, PageResponse
from app.middleware.logging import log_operation

router = APIRouter()


# ── Schemas ──────────────────────────────────────────────────────────────────

class CustomerCreate(BaseModel):
    name: str
    phone: str
    gender: Optional[Gender] = Gender.unknown
    source_id: Optional[int] = None
    budget_range: Optional[str] = None
    wedding_date: Optional[date] = None
    note: Optional[str] = None
    assigned_sale_id: Optional[int] = None


class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    gender: Optional[Gender] = None
    source_id: Optional[int] = None
    status: Optional[CustomerStatus] = None
    budget_range: Optional[str] = None
    wedding_date: Optional[date] = None
    note: Optional[str] = None
    assigned_sale_id: Optional[int] = None
    version: int


class FollowUpCreate(BaseModel):
    type: FollowUpType
    content: str
    next_follow_at: Optional[datetime] = None


class TransferRequest(BaseModel):
    target_sale_id: int


# ── Routes ───────────────────────────────────────────────────────────────────

@router.get("/customers")
async def list_customers(
    keyword: Optional[str] = Query(None),
    status: Optional[CustomerStatus] = Query(None),
    source_id: Optional[int] = Query(None),
    assigned_sale_id: Optional[int] = Query(None),
    date_start: Optional[date] = Query(None),
    date_end: Optional[date] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = select(Customer)

    if keyword:
        query = query.where(
            (Customer.name.like(f"%{keyword}%")) | (Customer.phone.like(f"%{keyword}%"))
        )
    if status:
        query = query.where(Customer.status == status)
    if source_id:
        query = query.where(Customer.source_id == source_id)
    if assigned_sale_id:
        query = query.where(Customer.assigned_sale_id == assigned_sale_id)
    if date_start:
        query = query.where(Customer.created_at >= date_start)
    if date_end:
        query = query.where(Customer.created_at <= date_end)

    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar_one()

    offset = (page - 1) * page_size
    query = query.order_by(Customer.created_at.desc()).offset(offset).limit(page_size)
    result = await db.execute(query)
    customers = result.scalars().all()

    return PageResponse(
        items=[_customer_to_dict(c) for c in customers],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/customers/{customer_id}")
async def get_customer(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Customer).where(Customer.id == customer_id))
    customer = result.scalar_one_or_none()
    if not customer:
        raise AppException(404, "NOT_FOUND", "客户不存在")

    fu_result = await db.execute(
        select(FollowUp)
        .where(FollowUp.customer_id == customer_id)
        .order_by(FollowUp.created_at.desc())
        .limit(10)
    )
    follow_ups = fu_result.scalars().all()

    return {
        **_customer_to_dict(customer),
        "follow_ups": [_followup_to_dict(fu) for fu in follow_ups],
    }


@router.post("/customers")
async def create_customer(
    body: CustomerCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    existing = await db.execute(select(Customer).where(Customer.phone == body.phone))
    if existing.scalar_one_or_none():
        raise AppException(400, "DUPLICATE_PHONE", "该手机号已存在")

    customer = Customer(
        name=body.name,
        phone=body.phone,
        gender=body.gender,
        source_id=body.source_id,
        status=CustomerStatus.potential,
        budget_range=body.budget_range,
        wedding_date=body.wedding_date,
        note=body.note,
        assigned_sale_id=body.assigned_sale_id,
    )
    db.add(customer)
    await db.commit()
    await db.refresh(customer)

    await log_operation(db, user.id, request, {"customer_id": customer.id, "name": customer.name})
    return _customer_to_dict(customer)


@router.put("/customers/{customer_id}")
async def update_customer(
    customer_id: int,
    body: CustomerUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Customer).where(Customer.id == customer_id))
    customer = result.scalar_one_or_none()
    if not customer:
        raise AppException(404, "NOT_FOUND", "客户不存在")

    if body.version != customer.updated_at.timestamp() if customer.updated_at else int(customer.created_at.timestamp()):
        raise AppException(409, "VERSION_CONFLICT", "数据已被其他人修改，请刷新后重试")

    update_data = body.model_dump(exclude_unset=True, exclude={"version"})
    for key, value in update_data.items():
        if value is not None:
            setattr(customer, key, value)

    await db.commit()
    await db.refresh(customer)

    await log_operation(db, user.id, request, {"customer_id": customer_id, "updated_fields": list(update_data.keys())})
    return _customer_to_dict(customer)


@router.post("/customers/{customer_id}/follow-ups")
async def add_follow_up(
    customer_id: int,
    body: FollowUpCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Customer).where(Customer.id == customer_id))
    customer = result.scalar_one_or_none()
    if not customer:
        raise AppException(404, "NOT_FOUND", "客户不存在")

    follow_up = FollowUp(
        customer_id=customer_id,
        sale_id=user.id,
        type=body.type,
        content=body.content,
        next_follow_at=body.next_follow_at,
    )
    db.add(follow_up)

    if customer.status == CustomerStatus.potential:
        customer.status = CustomerStatus.following

    await db.commit()
    await db.refresh(follow_up)

    await log_operation(db, user.id, request, {"customer_id": customer_id, "follow_up_id": follow_up.id})
    return _followup_to_dict(follow_up)


@router.post("/customers/{customer_id}/transfer")
async def transfer_customer(
    customer_id: int,
    body: TransferRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Customer).where(Customer.id == customer_id))
    customer = result.scalar_one_or_none()
    if not customer:
        raise AppException(404, "NOT_FOUND", "客户不存在")

    target_result = await db.execute(select(User).where(User.id == body.target_sale_id, User.status == "active"))
    if not target_result.scalar_one_or_none():
        raise AppException(404, "NOT_FOUND", "目标销售不存在")

    customer.assigned_sale_id = body.target_sale_id
    await db.commit()

    await log_operation(db, user.id, request, {
        "customer_id": customer_id,
        "from_sale_id": user.id,
        "to_sale_id": body.target_sale_id,
    })
    return _customer_to_dict(customer)


@router.post("/customers/{customer_id}/recycle")
async def recycle_customer(
    customer_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Customer).where(Customer.id == customer_id))
    customer = result.scalar_one_or_none()
    if not customer:
        raise AppException(404, "NOT_FOUND", "客户不存在")

    customer.assigned_sale_id = None
    customer.recycled_at = datetime.utcnow()
    await db.commit()

    await log_operation(db, user.id, request, {"customer_id": customer_id, "action": "recycle"})
    return _customer_to_dict(customer)


@router.get("/customer-pool")
async def list_customer_pool(
    keyword: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = select(Customer).where(Customer.assigned_sale_id.is_(None))

    if keyword:
        query = query.where(
            (Customer.name.like(f"%{keyword}%")) | (Customer.phone.like(f"%{keyword}%"))
        )

    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar_one()

    offset = (page - 1) * page_size
    query = query.order_by(Customer.recycled_at.desc()).offset(offset).limit(page_size)
    result = await db.execute(query)
    customers = result.scalars().all()

    return PageResponse(
        items=[_customer_to_dict(c) for c in customers],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.post("/customer-pool/{customer_id}/claim")
async def claim_customer(
    customer_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Customer).where(Customer.id == customer_id))
    customer = result.scalar_one_or_none()
    if not customer:
        raise AppException(404, "NOT_FOUND", "客户不存在")

    if customer.assigned_sale_id is not None:
        raise AppException(400, "ALREADY_ASSIGNED", "该客户已被认领")

    customer.assigned_sale_id = user.id
    customer.recycled_at = None
    customer.status = CustomerStatus.following
    await db.commit()

    await log_operation(db, user.id, request, {"customer_id": customer_id, "action": "claim"})
    return _customer_to_dict(customer)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _customer_to_dict(c: Customer) -> dict:
    return {
        "id": c.id,
        "name": c.name,
        "phone": c.phone,
        "gender": c.gender.value if c.gender else None,
        "source_id": c.source_id,
        "status": c.status.value if c.status else None,
        "budget_range": c.budget_range,
        "wedding_date": str(c.wedding_date) if c.wedding_date else None,
        "note": c.note,
        "assigned_sale_id": c.assigned_sale_id,
        "recycled_at": c.recycled_at.isoformat() if c.recycled_at else None,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
    }


def _followup_to_dict(fu: FollowUp) -> dict:
    return {
        "id": fu.id,
        "customer_id": fu.customer_id,
        "sale_id": fu.sale_id,
        "type": fu.type.value,
        "content": fu.content,
        "next_follow_at": fu.next_follow_at.isoformat() if fu.next_follow_at else None,
        "created_at": fu.created_at.isoformat() if fu.created_at else None,
    }
