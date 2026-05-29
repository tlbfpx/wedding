"""
退款数据访问层
"""
from __future__ import annotations
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.finance.domain.entities import Refund
from app.finance.domain.entities.enums import RefundStatus


class RefundRepository:
    """退款 Repository"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, refund_id: int) -> Optional[Refund]:
        """根据ID获取退款记录"""
        result = await self.db.execute(
            select(Refund).where(Refund.id == refund_id)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        order_id: int,
        amount: float,
        reason: str,
        created_by: int,
        note: Optional[str] = None,
    ) -> Refund:
        """创建退款记录"""
        refund = Refund(
            order_id=order_id,
            amount=amount,
            reason=reason,
            status=RefundStatus.pending_approval,
            note=note,
            created_by=created_by,
        )
        self.db.add(refund)
        await self.db.flush()
        await self.db.refresh(refund)
        return refund

    async def update(self, refund: Refund) -> Refund:
        """更新退款记录"""
        await self.db.flush()
        await self.db.refresh(refund)
        return refund

    async def list(
        self,
        order_id: Optional[int] = None,
        status: Optional[RefundStatus] = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Refund], int]:
        """查询退款列表"""
        from sqlalchemy import func

        query = select(Refund)

        if order_id:
            query = query.where(Refund.order_id == order_id)

        if status:
            query = query.where(Refund.status == status)

        # Count total
        count_result = await self.db.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar_one()

        # Fetch with pagination
        query = query.order_by(Refund.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(query)
        items = result.scalars().all()

        return list(items), total

    async def get_with_details(self, refund_id: int) -> Optional[Refund]:
        """获取退款详情（包含关联订单）"""
        result = await self.db.execute(
            select(Refund)
            .options(selectinload(Refund.order))
            .where(Refund.id == refund_id)
        )
        return result.scalar_one_or_none()
