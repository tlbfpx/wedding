"""
收款服务
"""
from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.finance.infrastructure.repositories import (
    FinancePaymentRepository,
    ReceivableRepository,
    TransactionRepository,
)
from app.finance.domain.entities import FinancePayment, Receivable, Transaction
from app.finance.domain.entities.enums import TransactionType, PaymentMethod
from app.events import DomainEvent, event_bus
from app.events.event_types import PAYMENT_RECORDED
from app.utils.errors import AppException


class PaymentService:
    """收款服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.payment_repo = FinancePaymentRepository(db)
        self.receivable_repo = ReceivableRepository(db)
        self.transaction_repo = TransactionRepository(db)

    async def record_payment(
        self,
        order_id: int,
        amount: float,
        method: PaymentMethod,
        paid_at: Optional[datetime] = None,
        note: Optional[str] = None,
        created_by: int = 0,
    ) -> FinancePayment:
        """登记收款

        Args:
            order_id: 订单ID
            amount: 收款金额
            method: 付款方式
            paid_at: 收款日期
            note: 备注
            created_by: 创建人ID

        Returns:
            FinancePayment: 收款记录

        Raises:
            AppException: 订单不存在或收款金额超过剩余应收
        """
        # 获取应收记录
        receivable = await self.receivable_repo.get_by_order(order_id)
        if not receivable:
            raise AppException(404, "RECEIVABLE_NOT_FOUND", "应收记录不存在")

        # 校验金额
        new_received = receivable.received_amount + Decimal(str(amount))
        if new_received > receivable.total_amount:
            raise AppException(400, "PAYMENT_EXCEEDS_TOTAL", "收款金额超过剩余应收")

        # 创建收款记录
        payment = await self.payment_repo.create(
            order_id=order_id,
            amount=amount,
            method=method.value if isinstance(method, PaymentMethod) else method,
            paid_at=paid_at or datetime.utcnow(),
            note=note,
            created_by=created_by,
        )

        # 更新应收
        receivable.received_amount = new_received
        await self._update_receivable_status(receivable)
        await self.receivable_repo.update(receivable)

        # 创建收入明细
        await self.transaction_repo.create(
            type=TransactionType.income,
            amount=Decimal(str(amount)),
            order_id=order_id,
            payment_id=payment.id,
            date=(paid_at or datetime.utcnow()).date(),
            method=method.value,
        )

        # 同时写入 Payment 表（兼容期）
        await self._create_legacy_payment(order_id, amount, method, paid_at, note)

        # 更新 Order.paid_amount
        from app.models.order import Order
        order_result = await self.db.execute(select(Order).where(Order.id == order_id))
        order = order_result.scalar_one_or_none()
        if order:
            order.paid_amount = float(Decimal(str(order.paid_amount)) + Decimal(str(amount)))

        await self.db.commit()
        await self.db.refresh(payment)

        # 发布事件
        await event_bus.publish(DomainEvent(
            event_type=PAYMENT_RECORDED,
            payload={
                "payment_id": payment.id,
                "order_id": order_id,
                "amount": str(amount),
                "method": method.value,
                "paid_at": (paid_at or datetime.utcnow()).isoformat(),
            }
        ))

        return payment

    async def _update_receivable_status(self, receivable: Receivable) -> None:
        """更新应收状态"""
        from app.finance.application.services.receivable_service import ReceivableService

        service = ReceivableService(self.db)
        await service._update_receivable_status(receivable)

    async def _create_legacy_payment(
        self,
        order_id: int,
        amount: float,
        method: PaymentMethod,
        paid_at: Optional[datetime],
        note: Optional[str],
    ) -> None:
        """创建兼容性 Payment 记录"""
        from app.models.order import Payment, PaymentStatus

        legacy_payment = Payment(
            order_id=order_id,
            amount=amount,
            method=method.value if isinstance(method, PaymentMethod) else method,
            status=PaymentStatus.confirmed,
            paid_at=paid_at or datetime.utcnow(),
            note=note,
        )
        self.db.add(legacy_payment)

    async def get_payment(self, payment_id: int) -> FinancePayment:
        """获取收款记录"""
        payment = await self.payment_repo.get(payment_id)
        if not payment:
            raise AppException(404, "PAYMENT_NOT_FOUND", "收款记录不存在")
        return payment

    async def update_payment(
        self,
        payment_id: int,
        amount: Optional[float] = None,
        method: Optional[PaymentMethod] = None,
        paid_at: Optional[datetime] = None,
        note: Optional[str] = None,
    ) -> FinancePayment:
        """修改收款记录"""
        payment = await self.payment_repo.get(payment_id)
        if not payment:
            raise AppException(404, "PAYMENT_NOT_FOUND", "收款记录不存在")

        # 更新字段
        if amount is not None:
            # 需要重新计算应收金额
            old_amount = Decimal(str(payment.amount))
            payment.amount = amount

            receivable = await self.receivable_repo.get_by_order(payment.order_id)
            if receivable:
                receivable.received_amount = receivable.received_amount - old_amount + Decimal(str(amount))
                await self._update_receivable_status(receivable)
                await self.receivable_repo.update(receivable)

        if method is not None:
            payment.method = method
        if paid_at is not None:
            payment.paid_at = paid_at
        if note is not None:
            payment.note = note

        result = await self.payment_repo.update(payment)
        await self.db.commit()
        return result

    async def delete_payment(self, payment_id: int) -> None:
        """删除收款记录"""
        payment = await self.payment_repo.get(payment_id)
        if not payment:
            raise AppException(404, "PAYMENT_NOT_FOUND", "收款记录不存在")

        # 重新计算应收金额
        receivable = await self.receivable_repo.get_by_order(payment.order_id)
        if receivable:
            receivable.received_amount = receivable.received_amount - Decimal(str(payment.amount))
            await self._update_receivable_status(receivable)
            await self.receivable_repo.update(receivable)

        # 先删除关联的交易记录（FK 约束）
        from app.finance.domain.entities import Transaction
        result = await self.db.execute(
            select(Transaction).where(Transaction.payment_id == payment_id)
        )
        transactions = result.scalars().all()
        for tx in transactions:
            await self.db.delete(tx)

        await self.payment_repo.delete(payment_id)

        # 更新 Order.paid_amount
        from app.models.order import Order
        order_result = await self.db.execute(select(Order).where(Order.id == payment.order_id))
        order = order_result.scalar_one_or_none()
        if order:
            order.paid_amount = float(max(0, Decimal(str(order.paid_amount)) - Decimal(str(payment.amount))))

        await self.db.commit()

    async def list_payments(
        self,
        order_id: Optional[int] = None,
        method: Optional[PaymentMethod] = None,
        date_start: Optional[date] = None,
        date_end: Optional[date] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[FinancePayment], int]:
        """查询收款列表"""
        offset = (page - 1) * page_size
        return await self.payment_repo.list(
            order_id=order_id,
            method=method,
            date_start=date_start,
            date_end=date_end,
            offset=offset,
            limit=page_size,
        )
