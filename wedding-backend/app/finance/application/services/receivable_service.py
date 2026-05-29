"""
应收账款服务
"""
from __future__ import annotations
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.finance.infrastructure.repositories import ReceivableRepository
from app.finance.domain.entities import Receivable
from app.finance.domain.entities.enums import ReceivableStatus
from app.events import DomainEvent, event_bus
from app.events.event_types import ORDER_STATUS_CHANGED
from app.utils.errors import AppException


class ReceivableService:
    """应收账款服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ReceivableRepository(db)

    async def create_receivable(
        self,
        order_id: int,
        total_amount: Decimal,
        due_days: int = 30,
    ) -> Receivable:
        """为订单创建应收记录

        Args:
            order_id: 订单ID
            total_amount: 应收总额
            due_days: 付款期限天数（默认签约后30天）

        Returns:
            Receivable: 应收记录

        Raises:
            AppException: 订单已存在应收记录
        """
        # 检查是否已存在应收
        existing = await self.repo.get_by_order(order_id)
        if existing:
            raise AppException(400, "RECEIVABLE_EXISTS", "订单已存在应收记录")

        # 创建应收记录
        receivable = await self.repo.create(
            order_id=order_id,
            total_amount=total_amount,
            received_amount=Decimal("0"),
            status=ReceivableStatus.unpaid,
            due_date=None,  # 签约时设置
        )

        # 发布事件
        from app.finance.domain.events.event_types import RECEIVABLE_CREATED
        await event_bus.publish(DomainEvent(
            event_type=RECEIVABLE_CREATED,
            payload={
                "receivable_id": receivable.id,
                "order_id": order_id,
                "total_amount": str(total_amount),
            }
        ))

        return receivable

    async def get_receivable_by_order(self, order_id: int) -> Optional[Receivable]:
        """根据订单ID获取应收记录"""
        return await self.repo.get_by_order(order_id)

    async def set_due_date(self, order_id: int, due_days: int = 30) -> Receivable:
        """设置应收到期日

        Args:
            order_id: 订单ID
            due_days: 付款期限天数

        Returns:
            Receivable: 更新后的应收记录
        """
        receivable = await self.repo.get_by_order(order_id)
        if not receivable:
            raise AppException(404, "RECEIVABLE_NOT_FOUND", "应收记录不存在")

        # 签约时计算到期日
        receivable.due_date = date.today() + timedelta(days=due_days)
        receivable = await self.repo.update(receivable)

        # 重新计算状态
        await self._update_receivable_status(receivable)

        return receivable

    async def update_receivable_status(self, receivable_id: int) -> None:
        """更新应收状态（根据已收金额自动计算）

        状态规则:
        - received_amount == 0: unpaid
        - 0 < received_amount < total_amount: partial
        - received_amount >= total_amount: paid
        - 当前日期 > due_date 且未全额收款: overdue
        """
        receivable = await self.repo.get(receivable_id)
        if not receivable:
            return

        await self._update_receivable_status(receivable)
        await self.repo.update(receivable)

    async def _update_receivable_status(self, receivable: Receivable) -> None:
        """内部方法：更新应收状态"""
        if receivable.received_amount <= 0:
            receivable.status = ReceivableStatus.unpaid
        elif receivable.received_amount < receivable.total_amount:
            receivable.status = ReceivableStatus.partial
        else:
            receivable.status = ReceivableStatus.paid

        # 检查逾期
        if receivable.due_date and date.today() > receivable.due_date:
            if receivable.received_amount < receivable.total_amount:
                old_status = receivable.status
                receivable.status = ReceivableStatus.overdue
                receivable.overdue_days = (date.today() - receivable.due_date).days

                # 如果状态从未逾期变为逾期，发布事件
                if old_status != ReceivableStatus.overdue:
                    from app.finance.domain.events.event_types import RECEIVABLE_OVERDUE
                    await event_bus.publish(DomainEvent(
                        event_type=RECEIVABLE_OVERDUE,
                        payload={
                            "receivable_id": receivable.id,
                            "order_id": receivable.order_id,
                            "due_date": receivable.due_date.isoformat() if receivable.due_date else None,
                            "overdue_days": receivable.overdue_days,
                        }
                    ))
        else:
            receivable.overdue_days = 0

    async def check_overdue_receivables(self) -> list[Receivable]:
        """获取逾期应收列表（用于定时任务）"""
        items, _ = await self.repo.list_overdue(limit=1000)
        return items
