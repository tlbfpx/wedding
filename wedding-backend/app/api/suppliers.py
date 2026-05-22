from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from decimal import Decimal

from app.database import get_db
from app.models import Supplier, SupplierService, SupplierEvaluation
from app.models.supplier import SupplierType, CooperationStatus
from app.middleware.auth import get_current_user
from app.models.user import User
from app.utils.errors import AppException
from app.utils.pagination import PageResponse
from app.middleware.logging import log_operation

router = APIRouter()


# ── Schemas ──────────────────────────────────────────────────────────────────

class SupplierCreate(BaseModel):
    name: str
    type: SupplierType
    contact: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    cooperation_status: Optional[CooperationStatus] = CooperationStatus.active
    note: Optional[str] = None


class SupplierUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[SupplierType] = None
    contact: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    cooperation_status: Optional[CooperationStatus] = None
    note: Optional[str] = None


class ServiceCreate(BaseModel):
    service_name: str
    description: Optional[str] = None
    price: float
    unit: Optional[str] = "次"
    note: Optional[str] = None


class ServiceUpdate(BaseModel):
    service_name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    unit: Optional[str] = None
    note: Optional[str] = None


class EvaluationCreate(BaseModel):
    order_id: int
    rating: int
    content: Optional[str] = None


# ── Supplier Routes ──────────────────────────────────────────────────────────

@router.get("")
async def list_suppliers(
    type: Optional[SupplierType] = Query(None),
    cooperation_status: Optional[CooperationStatus] = Query(None),
    keyword: Optional[str] = Query(None),
    rating_min: Optional[float] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = select(Supplier)

    if type:
        query = query.where(Supplier.type == type)
    if cooperation_status:
        query = query.where(Supplier.cooperation_status == cooperation_status)
    if keyword:
        query = query.where(
            (Supplier.name.like(f"%{keyword}%"))
            | (Supplier.contact.like(f"%{keyword}%"))
            | (Supplier.phone.like(f"%{keyword}%"))
        )
    if rating_min is not None:
        query = query.where(Supplier.rating >= rating_min)

    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar_one()

    offset = (page - 1) * page_size
    query = query.order_by(Supplier.created_at.desc()).offset(offset).limit(page_size)
    result = await db.execute(query)
    suppliers = result.scalars().all()

    return PageResponse(
        items=[_supplier_to_dict(s) for s in suppliers],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/{supplier_id}")
async def get_supplier(
    supplier_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Supplier).where(Supplier.id == supplier_id))
    supplier = result.scalar_one_or_none()
    if not supplier:
        raise AppException(404, "NOT_FOUND", "供应商不存在")

    svc_result = await db.execute(
        select(SupplierService).where(SupplierService.supplier_id == supplier_id)
    )
    services = svc_result.scalars().all()

    eval_result = await db.execute(
        select(SupplierEvaluation)
        .where(SupplierEvaluation.supplier_id == supplier_id)
        .order_by(SupplierEvaluation.created_at.desc())
        .limit(5)
    )
    evaluations = eval_result.scalars().all()

    return {
        **_supplier_to_dict(supplier),
        "services": [_service_to_dict(s) for s in services],
        "evaluations": [_evaluation_to_dict(e) for e in evaluations],
    }


@router.post("")
async def create_supplier(
    body: SupplierCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    supplier = Supplier(
        name=body.name,
        type=body.type,
        contact=body.contact,
        phone=body.phone,
        address=body.address,
        cooperation_status=body.cooperation_status or CooperationStatus.active,
        note=body.note,
    )
    db.add(supplier)
    await db.commit()
    await db.refresh(supplier)

    await log_operation(db, user.id, request, {"supplier_id": supplier.id, "name": supplier.name})
    return _supplier_to_dict(supplier)


@router.put("/{supplier_id}")
async def update_supplier(
    supplier_id: int,
    body: SupplierUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Supplier).where(Supplier.id == supplier_id))
    supplier = result.scalar_one_or_none()
    if not supplier:
        raise AppException(404, "NOT_FOUND", "供应商不存在")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(supplier, key, value)

    await db.commit()
    await db.refresh(supplier)

    await log_operation(db, user.id, request, {"supplier_id": supplier_id, "updated_fields": list(update_data.keys())})
    return _supplier_to_dict(supplier)


# ── Service Routes ───────────────────────────────────────────────────────────

@router.get("/{supplier_id}/services")
async def list_services(
    supplier_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(SupplierService).where(SupplierService.supplier_id == supplier_id)
    )
    services = result.scalars().all()
    return [_service_to_dict(s) for s in services]


@router.post("/{supplier_id}/services")
async def add_service(
    supplier_id: int,
    body: ServiceCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    supplier_result = await db.execute(select(Supplier).where(Supplier.id == supplier_id))
    if not supplier_result.scalar_one_or_none():
        raise AppException(404, "NOT_FOUND", "供应商不存在")

    service = SupplierService(
        supplier_id=supplier_id,
        service_name=body.service_name,
        description=body.description,
        price=body.price,
        unit=body.unit or "次",
        note=body.note,
    )
    db.add(service)
    await db.commit()
    await db.refresh(service)

    await log_operation(db, user.id, request, {"supplier_id": supplier_id, "service_id": service.id})
    return _service_to_dict(service)


@router.put("/{supplier_id}/services/{service_id}")
async def update_service(
    supplier_id: int,
    service_id: int,
    body: ServiceUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(SupplierService).where(
            SupplierService.id == service_id,
            SupplierService.supplier_id == supplier_id,
        )
    )
    service = result.scalar_one_or_none()
    if not service:
        raise AppException(404, "NOT_FOUND", "服务不存在")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(service, key, value)

    await db.commit()
    await db.refresh(service)

    await log_operation(db, user.id, request, {"supplier_id": supplier_id, "service_id": service_id})
    return _service_to_dict(service)


# ── Evaluation Routes ────────────────────────────────────────────────────────

@router.post("/{supplier_id}/evaluations")
async def add_evaluation(
    supplier_id: int,
    body: EvaluationCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    supplier_result = await db.execute(select(Supplier).where(Supplier.id == supplier_id))
    supplier = supplier_result.scalar_one_or_none()
    if not supplier:
        raise AppException(404, "NOT_FOUND", "供应商不存在")

    if not (1 <= body.rating <= 5):
        raise AppException(400, "INVALID_RATING", "评分必须在1-5之间")

    evaluation = SupplierEvaluation(
        supplier_id=supplier_id,
        order_id=body.order_id,
        rating=body.rating,
        content=body.content,
        evaluator_id=user.id,
    )
    db.add(evaluation)

    # Recalculate average rating
    avg_result = await db.execute(
        select(func.avg(SupplierEvaluation.rating), func.count(SupplierEvaluation.id))
        .where(SupplierEvaluation.supplier_id == supplier_id)
    )
    avg_rating, count = avg_result.one()
    # Include the new evaluation in the average
    new_avg = ((avg_rating or 0) * count + body.rating) / (count + 1)
    supplier.rating = round(new_avg, 1)

    await db.commit()
    await db.refresh(evaluation)

    await log_operation(db, user.id, request, {"supplier_id": supplier_id, "evaluation_id": evaluation.id, "rating": body.rating})
    return _evaluation_to_dict(evaluation)


@router.get("/{supplier_id}/evaluations")
async def list_evaluations(
    supplier_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = select(SupplierEvaluation).where(SupplierEvaluation.supplier_id == supplier_id)

    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar_one()

    offset = (page - 1) * page_size
    query = query.order_by(SupplierEvaluation.created_at.desc()).offset(offset).limit(page_size)
    result = await db.execute(query)
    evaluations = result.scalars().all()

    return PageResponse(
        items=[_evaluation_to_dict(e) for e in evaluations],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


# ── Helpers ──────────────────────────────────────────────────────────────────

def _supplier_to_dict(s: Supplier) -> dict:
    return {
        "id": s.id,
        "name": s.name,
        "type": s.type.value,
        "contact": s.contact,
        "phone": s.phone,
        "address": s.address,
        "cooperation_status": s.cooperation_status.value,
        "rating": float(s.rating),
        "note": s.note,
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
    }


def _service_to_dict(s: SupplierService) -> dict:
    return {
        "id": s.id,
        "supplier_id": s.supplier_id,
        "service_name": s.service_name,
        "description": s.description,
        "price": float(s.price),
        "unit": s.unit,
        "note": s.note,
    }


def _evaluation_to_dict(e: SupplierEvaluation) -> dict:
    return {
        "id": e.id,
        "supplier_id": e.supplier_id,
        "order_id": e.order_id,
        "rating": e.rating,
        "content": e.content,
        "evaluator_id": e.evaluator_id,
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }
