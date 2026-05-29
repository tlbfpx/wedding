"""
收支明细数据访问层
"""
from __future__ import annotations
from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.finance.domain.entities import Transaction
from app.finance.domain.entities.enums import TransactionType, ExpenseCategory


class TransactionRepository:
    """收支明细 Repository"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, transaction_id: int) -> Optional[Transaction]:
        """根据ID获取交易记录"""
        result = await self.db.execute(
            select(Transaction).where(Transaction.id == transaction_id)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        type: TransactionType,
        amount: Decimal,
        date: date,
        category: Optional[ExpenseCategory] = None,
        order_id: Optional[int] = None,
        payment_id: Optional[int] = None,
        refund_id: Optional[int] = None,
        supplier_id: Optional[int] = None,
        method: Optional[str] = None,
        note: Optional[str] = None,
    ) -> Transaction:
        """创建交易记录"""
        transaction = Transaction(
            type=type,
            category=category,
            amount=amount,
            order_id=order_id,
            payment_id=payment_id,
            refund_id=refund_id,
            supplier_id=supplier_id,
            date=date,
            method=method,
            note=note,
        )
        self.db.add(transaction)
        await self.db.flush()
        await self.db.refresh(transaction)
        return transaction

    async def update(self, transaction: Transaction) -> Transaction:
        """更新交易记录"""
        await self.db.flush()
        await self.db.refresh(transaction)
        return transaction

    async def list(
        self,
        type: Optional[TransactionType] = None,
        category: Optional[ExpenseCategory] = None,
        order_id: Optional[int] = None,
        supplier_id: Optional[int] = None,
        date_start: Optional[date] = None,
        date_end: Optional[date] = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Transaction], int]:
        """查询交易列表"""
        from sqlalchemy import func

        query = select(Transaction)

        if type:
            query = query.where(Transaction.type == type)

        if category:
            query = query.where(Transaction.category == category)

        if order_id:
            query = query.where(Transaction.order_id == order_id)

        if supplier_id:
            query = query.where(Transaction.supplier_id == supplier_id)

        if date_start:
            query = query.where(Transaction.date >= date_start)

        if date_end:
            query = query.where(Transaction.date <= date_end)

        # Count total
        count_result = await self.db.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar_one()

        # Fetch with pagination
        query = query.order_by(Transaction.date.desc()).offset(offset).limit(limit)
        result = await self.db.execute(query)
        items = result.scalars().all()

        return list(items), total

    async def get_summary(
        self, start_date: date, end_date: date
    ) -> dict:
        """获取收支汇总统计"""
        from sqlalchemy import func

        # 收入汇总
        income_result = await self.db.execute(
            select(func.sum(Transaction.amount))
            .where(Transaction.type == TransactionType.income)
            .where(Transaction.date >= start_date)
            .where(Transaction.date <= end_date)
        )
        income_total = income_result.scalar_one() or Decimal("0")

        # 支出汇总
        expense_result = await self.db.execute(
            select(func.sum(Transaction.amount))
            .where(Transaction.type == TransactionType.expense)
            .where(Transaction.date >= start_date)
            .where(Transaction.date <= end_date)
        )
        expense_total = expense_result.scalar_one() or Decimal("0")

        # 按分类汇总支出
        category_summary = {}
        for cat in ExpenseCategory:
            cat_result = await self.db.execute(
                select(func.sum(Transaction.amount))
                .where(Transaction.type == TransactionType.expense)
                .where(Transaction.category == cat)
                .where(Transaction.date >= start_date)
                .where(Transaction.date <= end_date)
            )
            category_summary[cat.value] = cat_result.scalar_one() or Decimal("0")

        return {
            "income_total": income_total,
            "expense_total": expense_total,
            "net_amount": income_total - expense_total,
            "by_category": category_summary,
        }
