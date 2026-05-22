from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.supplier import SupplierType, CooperationStatus
from app.middleware.auth import get_current_user
from app.models.user import User
from app.middleware.logging import log_operation
from app.schemas.supplier import (
    SupplierCreate,
    SupplierUpdate,
    ServiceCreate,
    ServiceUpdate,
    EvaluationCreate,
)
from app.services.supplier_service import SupplierService

router = APIRouter()


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
    svc = SupplierService(db)
    return await svc.list_suppliers(
        type=type,
        cooperation_status=cooperation_status,
        keyword=keyword,
        rating_min=rating_min,
        page=page,
        page_size=page_size,
    )


@router.get("/{supplier_id}")
async def get_supplier(
    supplier_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    svc = SupplierService(db)
    return await svc.get_supplier_detail(supplier_id)


@router.post("")
async def create_supplier(
    body: SupplierCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    svc = SupplierService(db)
    result = await svc.create_supplier(body)
    await log_operation(db, user.id, request, {"supplier_id": result["id"], "name": result["name"]})
    return result


@router.put("/{supplier_id}")
async def update_supplier(
    supplier_id: int,
    body: SupplierUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    svc = SupplierService(db)
    update_data = body.model_dump(exclude_unset=True)
    result = await svc.update_supplier(supplier_id, body)
    await log_operation(db, user.id, request, {"supplier_id": supplier_id, "updated_fields": list(update_data.keys())})
    return result


# ── Service Routes ───────────────────────────────────────────────────────────

@router.get("/{supplier_id}/services")
async def list_services(
    supplier_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    svc = SupplierService(db)
    return await svc.list_services(supplier_id)


@router.post("/{supplier_id}/services")
async def add_service(
    supplier_id: int,
    body: ServiceCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    svc = SupplierService(db)
    result = await svc.add_service(supplier_id, body)
    await log_operation(db, user.id, request, {"supplier_id": supplier_id, "service_id": result["id"]})
    return result


@router.put("/{supplier_id}/services/{service_id}")
async def update_service(
    supplier_id: int,
    service_id: int,
    body: ServiceUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    svc = SupplierService(db)
    result = await svc.update_service(supplier_id, service_id, body)
    await log_operation(db, user.id, request, {"supplier_id": supplier_id, "service_id": service_id})
    return result


# ── Evaluation Routes ────────────────────────────────────────────────────────

@router.post("/{supplier_id}/evaluations")
async def add_evaluation(
    supplier_id: int,
    body: EvaluationCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    svc = SupplierService(db)
    result = await svc.add_evaluation(supplier_id, body, user.id)
    await log_operation(db, user.id, request, {"supplier_id": supplier_id, "evaluation_id": result["id"], "rating": body.rating})
    return result


@router.get("/{supplier_id}/evaluations")
async def list_evaluations(
    supplier_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    svc = SupplierService(db)
    return await svc.list_evaluations(supplier_id, page, page_size)
