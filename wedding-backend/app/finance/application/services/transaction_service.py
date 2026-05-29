"""
收支明细服务
"""
from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.finance.infrastructure.repositories import TransactionRepository
from app.finance.domain.entities import Transaction
from app.finance.domain.entities.enums import TransactionType, ExpenseCategory, PaymentMethod
from app.events import DomainEvent, event_bus
from app.events.event_types import PAYMENT_RECORDED
from app.utils.errors import AppException


class TransactionService:
    """收支明细服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.transaction_repo = TransactionRepository(db)

    async def create_income_transaction(
        self,
        payment_id: int,
        order_id: int,
        amount: float,
        method: PaymentMethod,
        paid_at: datetime,
    ) -> Transaction:
        """创建收入记录（收款时自动生成）

        Args:
            payment_id: 收款记录ID
            order_id: 订单ID
            amount: 金额
            method: 付款方式
            paid_at: 收款日期

        Returns:
            Transaction: 收入记录
        """
        transaction = await self.transaction_repo.create(
            type=TransactionType.income,
            amount=Decimal(str(amount)),
            order_id=order_id,
            payment_id=payment_id,
            date=paid_at.date(),
            method=method.value,
        )

        # 发布事件
        from app.finance.domain.events.event_types import TRANSACTION_CREATED
        await event_bus.publish(DomainEvent(
            event_type=TRANSACTION_CREATED,
            payload={
                "transaction_id": transaction.id,
                "type": TransactionType.income.value,
                "amount": str(amount),
            }
        ))

        return transaction

    async def create_expense_transaction(
        self,
        category: ExpenseCategory,
        amount: float,
        order_id: Optional[int] = None,
        supplier_id: Optional[int] = None,
        date: Optional[date] = None,
        note: Optional[str] = None,
        created_by: Optional[int] = None,
    ) -> Transaction:
        """创建支出记录（手动登记）"""
        transaction = await self.transaction_repo.create(
            type=TransactionType.expense,
            category=category,
            amount=Decimal(str(amount)),
            order_id=order_id,
            supplier_id=supplier_id,
            date=date or date.today(),
            note=note,
        )

        # 发布事件
        from app.finance.domain.events.event_types import TRANSACTION_CREATED
        await event_bus.publish(DomainEvent(
            event_type=TRANSACTION_CREATED,
            payload={
                "transaction_id": transaction.id,
                "type": TransactionType.expense.value,
                "category": category.value,
                "amount": str(amount),
                "created_by": created_by,
            }
        ))

        return transaction

    async def create_refund_transaction(
        self,
        refund_id: int,
        order_id: int,
        amount: float,
        refunded_at: datetime,
    ) -> Transaction:
        """创建退款支出记录"""
        transaction = await self.transaction_repo.create(
            type=TransactionType.expense,
            category=ExpenseCategory.refund,
            amount=Decimal(str(amount)),
            order_id=order_id,
            refund_id=refund_id,
            date=refunded_at.date(),
            note="退款支出",
        )

        # 发布事件
        from app.finance.domain.events.event_types import TRANSACTION_CREATED
        await event_bus.publish(DomainEvent(
            event_type=TRANSACTION_CREATED,
            payload={
                "transaction_id": transaction.id,
                "type": TransactionType.expense.value,
                "category": ExpenseCategory.refund.value,
                "amount": str(amount),
            }
        ))

        return transaction

    async def get_transaction(self, transaction_id: int) -> Transaction:
        """获取交易记录"""
        transaction = await self.transaction_repo.get(transaction_id)
        if not transaction:
            raise AppException(404, "TRANSACTION_NOT_FOUND", "交易记录不存在")
        return transaction

    async def update_transaction(
        self,
        transaction_id: int,
        amount: Optional[float] = None,
        category: Optional[ExpenseCategory] = None,
        note: Optional[str] = None,
    ) -> Transaction:
        """修改支出记录"""
        transaction = await self.transaction_repo.get(transaction_id)
        if not transaction:
            raise AppException(404, "TRANSACTION_NOT_FOUND", "交易记录不存在")

        if transaction.type != TransactionType.expense:
            raise AppException(400, "INVALID_OPERATION", "收入记录不可修改")

        if amount is not None:
            transaction.amount = Decimal(str(amount))
        if category is not None:
            transaction.category = category
        if note is not None:
            transaction.note = note

        return await self.transaction_repo.update(transaction)

    async def list_transactions(
        self,
        type: Optional[TransactionType] = None,
        category: Optional[ExpenseCategory] = None,
        order_id: Optional[int] = None,
        supplier_id: Optional[int] = None,
        date_start: Optional[date] = None,
        date_end: Optional[date] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Transaction], int]:
        """查询交易列表"""
        offset = (page - 1) * page_size
        return await self.transaction_repo.list(
            type=type,
            category=category,
            order_id=order_id,
            supplier_id=supplier_id,
            date_start=date_start,
            date_end=date_end,
            offset=offset,
            limit=page_size,
        )

    async def get_summary(
        self, start_date: date, end_date: date
    ) -> dict:
        """获取收支汇总统计"""
        return await self.transaction_repo.get_summary(start_date, end_date)
