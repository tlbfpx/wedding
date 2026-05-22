from __future__ import annotations
from datetime import date
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_db
from app.models.customer import CustomerStatus
from app.middleware.auth import require_permission
from app.utils.pagination import PageResponse
from app.middleware.logging import log_operation
from app.schemas.customer import CustomerCreate, CustomerUpdate, FollowUpCreate, TransferRequest
from app.services.customer_service import CustomerService

router = APIRouter()


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
    ctx: dict = Depends(require_permission("crm", "read")),
):
    svc = CustomerService(db)
    items, total = await svc.list_customers(
        keyword=keyword,
        status=status,
        source_id=source_id,
        assigned_sale_id=assigned_sale_id,
        date_start=date_start,
        date_end=date_end,
        page=page,
        page_size=page_size,
        scope=ctx["scope"],
        user_id=ctx["user"].id,
    )
    return PageResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/customers/{customer_id}")
async def get_customer(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(require_permission("crm", "read")),
):
    svc = CustomerService(db)
    return await svc.get_customer_detail(customer_id)


@router.post("/customers")
async def create_customer(
    body: CustomerCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(require_permission("crm", "write")),
):
    svc = CustomerService(db)
    result, customer = await svc.create_customer(body)
    await log_operation(db, ctx["user"].id, request, {"customer_id": customer.id, "name": customer.name})
    return result


@router.put("/customers/{customer_id}")
async def update_customer(
    customer_id: int,
    body: CustomerUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(require_permission("crm", "write")),
):
    svc = CustomerService(db)
    result, updated_fields = await svc.update_customer(customer_id, body)
    await log_operation(db, ctx["user"].id, request, {"customer_id": customer_id, "updated_fields": updated_fields})
    return result


@router.post("/customers/{customer_id}/follow-ups")
async def add_follow_up(
    customer_id: int,
    body: FollowUpCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(require_permission("crm", "write")),
):
    svc = CustomerService(db)
    result, follow_up = await svc.add_follow_up(customer_id, body, ctx["user"].id)
    await log_operation(db, ctx["user"].id, request, {"customer_id": customer_id, "follow_up_id": follow_up.id})
    return result


@router.post("/customers/{customer_id}/transfer")
async def transfer_customer(
    customer_id: int,
    body: TransferRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(require_permission("crm", "write")),
):
    svc = CustomerService(db)
    result = await svc.transfer_customer(customer_id, body.target_sale_id)
    await log_operation(db, ctx["user"].id, request, {
        "customer_id": customer_id,
        "to_sale_id": body.target_sale_id,
    })
    return result


@router.post("/customers/{customer_id}/recycle")
async def recycle_customer(
    customer_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(require_permission("crm", "write")),
):
    svc = CustomerService(db)
    result = await svc.recycle_customer(customer_id)
    await log_operation(db, ctx["user"].id, request, {"customer_id": customer_id, "action": "recycle"})
    return result


@router.get("/customer-pool")
async def list_customer_pool(
    keyword: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(require_permission("crm", "read")),
):
    svc = CustomerService(db)
    items, total = await svc.list_customer_pool(
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    return PageResponse(
        items=items,
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
    ctx: dict = Depends(require_permission("crm", "write")),
):
    svc = CustomerService(db)
    result = await svc.claim_customer(customer_id, ctx["user"].id)
    await log_operation(db, ctx["user"].id, request, {"customer_id": customer_id, "action": "claim"})
    return result
