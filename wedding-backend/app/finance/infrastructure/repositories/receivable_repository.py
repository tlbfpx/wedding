"""
应收账款数据访问层
"""
from __future__ import annotations
from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.finance.domain.entities import Receivable
from app.finance.domain.entities.enums import ReceivableStatus
from app.models.order import Order


class ReceivableRepository:
    """应收账款 Repository"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_order(self, order_id: int) -> Optional[Receivable]:
        """根据订单ID获取应收记录"""
        result = await self.db.execute(
            select(Receivable).where(Receivable.order_id == order_id)
        )
        return result.scalar_one_or_none()

    async def get(self, receivable_id: int) -> Optional[Receivable]:
        """根据ID获取应收记录"""
        result = await self.db.execute(
            select(Receivable).where(Receivable.id == receivable_id)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        order_id: int,
        total_amount: Decimal,
        received_amount: Decimal,
        status: ReceivableStatus,
        due_date: Optional[date] = None,
    ) -> Receivable:
        """创建应收记录"""
        receivable = Receivable(
            order_id=order_id,
            total_amount=total_amount,
            received_amount=received_amount,
            status=status,
            due_date=due_date,
            overdue_days=0,
        )
        self.db.add(receivable)
        await self.db.flush()
        await self.db.refresh(receivable)
        return receivable

    async def update(self, receivable: Receivable) -> Receivable:
        """更新应收记录"""
        await self.db.flush()
        await self.db.refresh(receivable)
        return receivable

    async def list(
        self,
        status: Optional[ReceivableStatus] = None,
        sale_id: Optional[int] = None,
        date_start: Optional[date] = None,
        date_end: Optional[date] = None,
        keyword: Optional[str] = None,
        is_overdue: Optional[bool] = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Receivable], int]:
        """查询应收列表"""
        from sqlalchemy import func, or_

        query = select(Receivable).join(Order)

        if status:
            query = query.where(Receivable.status == status)

        if sale_id:
            query = query.where(Order.sale_id == sale_id)

        if date_start:
            query = query.where(Receivable.created_at >= date_start)

        if date_end:
            query = query.where(Receivable.created_at <= date_end)

        if keyword:
            query = query.where(Order.order_no.like(f"%{keyword}%"))

        if is_overdue is not None:
            if is_overdue:
                query = query.where(
                    and_(
                        Receivable.due_date < date.today(),
                        Receivable.received_amount < Receivable.total_amount,
                    )
                )
            else:
                query = query.where(
                    or_(
                        Receivable.due_date >= date.today(),
                        Receivable.received_amount >= Receivable.total_amount,
                    )
                )

        # Count total
        count_result = await self.db.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar_one()

        # Fetch with pagination
        query = query.order_by(Receivable.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(query)
        items = result.scalars().all()

        return list(items), total

    async def list_overdue(
        self, offset: int = 0, limit: int = 20
    ) -> tuple[list[Receivable], int]:
        """查询逾期应收列表"""
        return await self.list(is_overdue=True, offset=offset, limit=limit)

    async def get_with_details(self, receivable_id: int) -> Optional[Receivable]:
        """获取应收详情（包含关联订单和收款记录）"""
        result = await self.db.execute(
            select(Receivable)
            .options(selectinload(Receivable.order))
            .where(Receivable.id == receivable_id)
        )
        return result.scalar_one_or_none()
