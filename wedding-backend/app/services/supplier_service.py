from __future__ import annotations

from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Supplier, SupplierService, SupplierEvaluation
from app.models.supplier import SupplierType, CooperationStatus
from app.schemas.supplier import (
    SupplierCreate,
    SupplierUpdate,
    ServiceCreate,
    ServiceUpdate,
    EvaluationCreate,
)
from app.utils.errors import AppException
from app.utils.pagination import PageResponse


class SupplierService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_suppliers(
        self,
        type: Optional[SupplierType] = None,
        cooperation_status: Optional[CooperationStatus] = None,
        keyword: Optional[str] = None,
        rating_min: Optional[float] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PageResponse:
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

        total_result = await self.db.execute(select(func.count()).select_from(query.subquery()))
        total = total_result.scalar_one()

        offset = (page - 1) * page_size
        query = query.order_by(Supplier.created_at.desc()).offset(offset).limit(page_size)
        result = await self.db.execute(query)
        suppliers = result.scalars().all()

        return PageResponse(
            items=[_supplier_to_dict(s) for s in suppliers],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=(total + page_size - 1) // page_size,
        )

    async def get_supplier_detail(self, supplier_id: int) -> dict:
        result = await self.db.execute(select(Supplier).where(Supplier.id == supplier_id))
        supplier = result.scalar_one_or_none()
        if not supplier:
            raise AppException(404, "NOT_FOUND", "供应商不存在")

        svc_result = await self.db.execute(
            select(SupplierService).where(SupplierService.supplier_id == supplier_id)
        )
        services = svc_result.scalars().all()

        eval_result = await self.db.execute(
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

    async def create_supplier(self, data: SupplierCreate) -> dict:
        supplier = Supplier(
            name=data.name,
            type=data.type,
            contact=data.contact,
            phone=data.phone,
            address=data.address,
            cooperation_status=data.cooperation_status or CooperationStatus.active,
            note=data.note,
        )
        self.db.add(supplier)
        await self.db.commit()
        await self.db.refresh(supplier)
        return _supplier_to_dict(supplier)

    async def update_supplier(self, supplier_id: int, data: SupplierUpdate) -> dict:
        result = await self.db.execute(select(Supplier).where(Supplier.id == supplier_id))
        supplier = result.scalar_one_or_none()
        if not supplier:
            raise AppException(404, "NOT_FOUND", "供应商不存在")

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(supplier, key, value)

        await self.db.commit()
        await self.db.refresh(supplier)
        return _supplier_to_dict(supplier)

    async def list_services(self, supplier_id: int) -> list[dict]:
        result = await self.db.execute(
            select(SupplierService).where(SupplierService.supplier_id == supplier_id)
        )
        services = result.scalars().all()
        return [_service_to_dict(s) for s in services]

    async def add_service(self, supplier_id: int, data: ServiceCreate) -> dict:
        supplier_result = await self.db.execute(select(Supplier).where(Supplier.id == supplier_id))
        if not supplier_result.scalar_one_or_none():
            raise AppException(404, "NOT_FOUND", "供应商不存在")

        service = SupplierService(
            supplier_id=supplier_id,
            service_name=data.service_name,
            description=data.description,
            price=data.price,
            unit=data.unit or "次",
            note=data.note,
        )
        self.db.add(service)
        await self.db.commit()
        await self.db.refresh(service)
        return _service_to_dict(service)

    async def update_service(
        self, supplier_id: int, service_id: int, data: ServiceUpdate
    ) -> dict:
        result = await self.db.execute(
            select(SupplierService).where(
                SupplierService.id == service_id,
                SupplierService.supplier_id == supplier_id,
            )
        )
        service = result.scalar_one_or_none()
        if not service:
            raise AppException(404, "NOT_FOUND", "服务不存在")

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(service, key, value)

        await self.db.commit()
        await self.db.refresh(service)
        return _service_to_dict(service)

    async def add_evaluation(
        self, supplier_id: int, data: EvaluationCreate, user_id: int
    ) -> dict:
        supplier_result = await self.db.execute(
            select(Supplier).where(Supplier.id == supplier_id)
        )
        supplier = supplier_result.scalar_one_or_none()
        if not supplier:
            raise AppException(404, "NOT_FOUND", "供应商不存在")

        if not (1 <= data.rating <= 5):
            raise AppException(400, "INVALID_RATING", "评分必须在1-5之间")

        evaluation = SupplierEvaluation(
            supplier_id=supplier_id,
            order_id=data.order_id,
            rating=data.rating,
            content=data.content,
            evaluator_id=user_id,
        )
        self.db.add(evaluation)
        await self.db.flush()

        await self._recalculate_rating(supplier_id)

        await self.db.commit()
        await self.db.refresh(evaluation)
        return _evaluation_to_dict(evaluation)

    async def _recalculate_rating(
        self, supplier_id: int
    ) -> None:
        """Recalculate average rating from all persisted evaluations."""
        avg_result = await self.db.execute(
            select(func.avg(SupplierEvaluation.rating))
            .where(SupplierEvaluation.supplier_id == supplier_id)
        )
        avg_rating = avg_result.scalar_one()

        supplier_result = await self.db.execute(
            select(Supplier).where(Supplier.id == supplier_id)
        )
        supplier = supplier_result.scalar_one()
        supplier.rating = round(float(avg_rating or 0), 1)

    async def list_evaluations(
        self, supplier_id: int, page: int = 1, page_size: int = 20
    ) -> PageResponse:
        query = select(SupplierEvaluation).where(SupplierEvaluation.supplier_id == supplier_id)

        total_result = await self.db.execute(select(func.count()).select_from(query.subquery()))
        total = total_result.scalar_one()

        offset = (page - 1) * page_size
        query = query.order_by(SupplierEvaluation.created_at.desc()).offset(offset).limit(page_size)
        result = await self.db.execute(query)
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
