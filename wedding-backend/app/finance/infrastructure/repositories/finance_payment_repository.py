"""
财务收款数据访问层
"""
from __future__ import annotations
from datetime import date
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.finance.domain.entities import FinancePayment
from app.finance.domain.entities.enums import PaymentMethod


class FinancePaymentRepository:
    """财务收款 Repository"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, payment_id: int) -> Optional[FinancePayment]:
        """根据ID获取收款记录"""
        result = await self.db.execute(
            select(FinancePayment).where(FinancePayment.id == payment_id)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        order_id: int,
        amount: float,
        method: PaymentMethod,
        paid_at: date,
        note: Optional[str] = None,
        created_by: int = 0,
    ) -> FinancePayment:
        """创建收款记录"""
        payment = FinancePayment(
            order_id=order_id,
            amount=amount,
            method=method.value if isinstance(method, PaymentMethod) else method,
            paid_at=paid_at,
            note=note,
            created_by=created_by,
        )
        self.db.add(payment)
        await self.db.flush()
        await self.db.refresh(payment)
        return payment

    async def update(self, payment: FinancePayment) -> FinancePayment:
        """更新收款记录"""
        await self.db.flush()
        await self.db.refresh(payment)
        return payment

    async def delete(self, payment_id: int) -> None:
        """删除收款记录"""
        payment = await self.get(payment_id)
        if payment:
            await self.db.delete(payment)

    async def list(
        self,
        order_id: Optional[int] = None,
        method: Optional[PaymentMethod] = None,
        date_start: Optional[date] = None,
        date_end: Optional[date] = None,
        created_by: Optional[int] = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[FinancePayment], int]:
        """查询收款列表"""
        from sqlalchemy import func

        query = select(FinancePayment)

        if order_id:
            query = query.where(FinancePayment.order_id == order_id)

        if method:
            query = query.where(FinancePayment.method == method)

        if date_start:
            query = query.where(FinancePayment.paid_at >= date_start)

        if date_end:
            query = query.where(FinancePayment.paid_at <= date_end)

        if created_by:
            query = query.where(FinancePayment.created_by == created_by)

        # Count total
        count_result = await self.db.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar_one()

        # Fetch with pagination
        query = query.order_by(FinancePayment.paid_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(query)
        items = result.scalars().all()

        return list(items), total

    async def get_with_details(self, payment_id: int) -> Optional[FinancePayment]:
        """获取收款详情（包含关联订单）"""
        result = await self.db.execute(
            select(FinancePayment)
            .options(selectinload(FinancePayment.order))
            .where(FinancePayment.id == payment_id)
        )
        return result.scalar_one_or_none()
