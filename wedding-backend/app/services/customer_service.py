from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Customer, FollowUp
from app.models.customer import CustomerStatus
from app.models.user import User
from app.utils.errors import AppException


class CustomerService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_customers(
        self,
        keyword: Optional[str],
        status: Optional[CustomerStatus],
        source_id: Optional[int],
        assigned_sale_id: Optional[int],
        date_start: Optional[datetime],
        date_end: Optional[datetime],
        page: int,
        page_size: int,
        scope: str = "all",
        user_id: Optional[int] = None,
    ) -> tuple[list[dict], int]:
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
        if scope == "own" and user_id:
            query = query.where(Customer.assigned_sale_id == user_id)

        total_result = await self.db.execute(select(func.count()).select_from(query.subquery()))
        total = total_result.scalar_one()

        offset = (page - 1) * page_size
        query = query.order_by(Customer.created_at.desc()).offset(offset).limit(page_size)
        result = await self.db.execute(query)
        customers = result.scalars().all()

        items = [_customer_to_dict(c) for c in customers]
        return items, total

    async def get_customer_detail(self, customer_id: int) -> dict:
        result = await self.db.execute(select(Customer).where(Customer.id == customer_id))
        customer = result.scalar_one_or_none()
        if not customer:
            raise AppException(404, "NOT_FOUND", "客户不存在")

        fu_result = await self.db.execute(
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

    async def create_customer(self, data) -> dict:
        existing = await self.db.execute(select(Customer).where(Customer.phone == data.phone))
        if existing.scalar_one_or_none():
            raise AppException(400, "DUPLICATE_PHONE", "该手机号已存在")

        customer = Customer(
            name=data.name,
            phone=data.phone,
            gender=data.gender,
            source_id=data.source_id,
            status=CustomerStatus.potential,
            budget_range=data.budget_range,
            wedding_date=data.wedding_date,
            note=data.note,
            assigned_sale_id=data.assigned_sale_id,
        )
        self.db.add(customer)
        await self.db.commit()
        await self.db.refresh(customer)

        return _customer_to_dict(customer), customer

    async def update_customer(self, customer_id: int, data) -> dict:
        result = await self.db.execute(select(Customer).where(Customer.id == customer_id))
        customer = result.scalar_one_or_none()
        if not customer:
            raise AppException(404, "NOT_FOUND", "客户不存在")

        current_version = int(customer.updated_at.timestamp()) if customer.updated_at else int(customer.created_at.timestamp())
        if data.version != current_version:
            raise AppException(409, "VERSION_CONFLICT", "数据已被其他人修改，请刷新后重试")

        update_data = data.model_dump(exclude_unset=True, exclude={"version"})

        # Validate phone uniqueness when phone is being changed
        if update_data.get("phone") is not None and update_data["phone"] != customer.phone:
            existing = await self.db.execute(
                select(Customer).where(
                    Customer.phone == update_data["phone"],
                    Customer.id != customer_id,
                )
            )
            if existing.scalar_one_or_none():
                raise AppException(400, "DUPLICATE_PHONE", "手机号已被使用")

        for key, value in update_data.items():
            if value is not None:
                setattr(customer, key, value)

        await self.db.commit()
        await self.db.refresh(customer)

        return _customer_to_dict(customer), list(update_data.keys())

    async def add_follow_up(self, customer_id: int, data, user_id: int) -> dict:
        result = await self.db.execute(select(Customer).where(Customer.id == customer_id))
        customer = result.scalar_one_or_none()
        if not customer:
            raise AppException(404, "NOT_FOUND", "客户不存在")

        follow_up = FollowUp(
            customer_id=customer_id,
            sale_id=user_id,
            type=data.type,
            content=data.content,
            next_follow_at=data.next_follow_at,
        )
        self.db.add(follow_up)

        if customer.status == CustomerStatus.potential:
            customer.status = CustomerStatus.following

        await self.db.commit()
        await self.db.refresh(follow_up)

        return _followup_to_dict(follow_up), follow_up

    async def transfer_customer(self, customer_id: int, target_sale_id: int) -> dict:
        result = await self.db.execute(select(Customer).where(Customer.id == customer_id))
        customer = result.scalar_one_or_none()
        if not customer:
            raise AppException(404, "NOT_FOUND", "客户不存在")

        target_result = await self.db.execute(select(User).where(User.id == target_sale_id, User.status == "active"))
        if not target_result.scalar_one_or_none():
            raise AppException(404, "NOT_FOUND", "目标销售不存在")

        customer.assigned_sale_id = target_sale_id
        await self.db.commit()

        return _customer_to_dict(customer)

    async def recycle_customer(self, customer_id: int) -> dict:
        result = await self.db.execute(select(Customer).where(Customer.id == customer_id))
        customer = result.scalar_one_or_none()
        if not customer:
            raise AppException(404, "NOT_FOUND", "客户不存在")

        customer.assigned_sale_id = None
        customer.recycled_at = datetime.utcnow()
        await self.db.commit()

        return _customer_to_dict(customer)

    async def list_customer_pool(
        self,
        keyword: Optional[str],
        page: int,
        page_size: int,
    ) -> tuple[list[dict], int]:
        query = select(Customer).where(Customer.assigned_sale_id.is_(None))

        if keyword:
            query = query.where(
                (Customer.name.like(f"%{keyword}%")) | (Customer.phone.like(f"%{keyword}%"))
            )

        total_result = await self.db.execute(select(func.count()).select_from(query.subquery()))
        total = total_result.scalar_one()

        offset = (page - 1) * page_size
        query = query.order_by(Customer.recycled_at.desc()).offset(offset).limit(page_size)
        result = await self.db.execute(query)
        customers = result.scalars().all()

        items = [_customer_to_dict(c) for c in customers]
        return items, total

    async def claim_customer(self, customer_id: int, user_id: int) -> dict:
        result = await self.db.execute(select(Customer).where(Customer.id == customer_id))
        customer = result.scalar_one_or_none()
        if not customer:
            raise AppException(404, "NOT_FOUND", "客户不存在")

        if customer.assigned_sale_id is not None:
            raise AppException(400, "ALREADY_ASSIGNED", "该客户已被认领")

        customer.assigned_sale_id = user_id
        customer.recycled_at = None
        customer.status = CustomerStatus.following
        await self.db.commit()

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
