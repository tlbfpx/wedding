"""
对账数据访问层
"""
from __future__ import annotations
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.finance.domain.entities import Reconciliation


class ReconciliationRepository:
    """对账 Repository"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, reconciliation_id: int) -> Optional[Reconciliation]:
        """根据ID获取对账记录"""
        result = await self.db.execute(
            select(Reconciliation).where(Reconciliation.id == reconciliation_id)
        )
        return result.scalar_one_or_none()

    async def get_by_period(self, period: str) -> Optional[Reconciliation]:
        """根据周期获取对账记录"""
        result = await self.db.execute(
            select(Reconciliation).where(Reconciliation.period == period)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        period: str,
        snapshot: str,
        confirmed_by: int,
        notes: Optional[str] = None,
    ) -> Reconciliation:
        """创建对账记录"""
        from datetime import datetime

        reconciliation = Reconciliation(
            period=period,
            snapshot=snapshot,
            notes=notes,
            confirmed_by=confirmed_by,
            confirmed_at=datetime.utcnow(),
        )
        self.db.add(reconciliation)
        await self.db.flush()
        await self.db.refresh(reconciliation)
        return reconciliation

    async def list(
        self, offset: int = 0, limit: int = 20
    ) -> tuple[list[Reconciliation], int]:
        """查询对账列表"""
        from sqlalchemy import func

        query = select(Reconciliation)

        # Count total
        count_result = await self.db.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar_one()

        # Fetch with pagination
        query = query.order_by(Reconciliation.confirmed_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(query)
        items = result.scalars().all()

        return list(items), total
