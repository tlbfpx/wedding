"""
对账服务
"""
from __future__ import annotations
import json
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.finance.infrastructure.repositories import ReconciliationRepository, ReceivableRepository, TransactionRepository
from app.finance.domain.entities import Reconciliation, Receivable
from app.finance.domain.entities.enums import ReceivableStatus, TransactionType, ExpenseCategory
from app.events import DomainEvent, event_bus
from app.utils.errors import AppException


class ReconciliationService:
    """对账服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.reconciliation_repo = ReconciliationRepository(db)
        self.receivable_repo = ReceivableRepository(db)
        self.transaction_repo = TransactionRepository(db)

    async def generate_report(self, period: str) -> dict:
        """生成对账报表

        Args:
            period: 对账周期，格式 "YYYY-MM"（月度）或 "YYYY-QQ"（季度）

        Returns:
            dict: 对账报表
        """
        start_date, end_date = self._parse_period(period)

        # 收入对账
        income_reconciliation = await self._generate_income_reconciliation(start_date, end_date)

        # 支出对账
        expense_reconciliation = await self._generate_expense_reconciliation(start_date, end_date)

        return {
            "period": period,
            "income_reconciliation": income_reconciliation,
            "expense_reconciliation": expense_reconciliation,
            "generated_at": datetime.utcnow().isoformat(),
        }

    async def confirm_reconciliation(
        self, period: str, notes: Optional[str] = None, user_id: int = 0
    ) -> Reconciliation:
        """确认对账

        Args:
            period: 对账周期
            notes: 备注
            user_id: 确认人ID

        Returns:
            Reconciliation: 对账记录

        Raises:
            AppException: 对账周期已存在
        """
        # 检查是否已存在
        existing = await self.reconciliation_repo.get_by_period(period)
        if existing:
            raise AppException(400, "RECONCILIATION_EXISTS", "该周期对账记录已存在")

        # 生成报告
        report = await self.generate_report(period)

        # 创建对账记录
        reconciliation = await self.reconciliation_repo.create(
            period=period,
            snapshot=json.dumps(report, ensure_ascii=False),
            notes=notes,
            confirmed_by=user_id,
        )

        # 发布事件
        from app.finance.domain.events.event_types import RECONCILIATION_CONFIRMED
        await event_bus.publish(DomainEvent(
            event_type=RECONCILIATION_CONFIRMED,
            payload={
                "reconciliation_id": reconciliation.id,
                "period": period,
                "notes": notes,
            }
        ))

        return reconciliation

    async def get_history(
        self, page: int = 1, page_size: int = 20
    ) -> tuple[list[Reconciliation], int]:
        """获取对账历史"""
        offset = (page - 1) * page_size
        return await self.reconciliation_repo.list(offset=offset, limit=page_size)

    async def get_reconciliation(self, reconciliation_id: int) -> Reconciliation:
        """获取对账记录"""
        reconciliation = await self.reconciliation_repo.get(reconciliation_id)
        if not reconciliation:
            raise AppException(404, "RECONCILIATION_NOT_FOUND", "对账记录不存在")
        return reconciliation

    def _parse_period(self, period: str) -> tuple[date, date]:
        """解析对账周期，返回起止日期"""
        if "-Q" in period:
            # 季度: YYYY-QQ
            year, quarter = period.split("-Q")
            year = int(year)
            quarter = int(quarter)

            if quarter == 1:
                start_date = date(year, 1, 1)
                end_date = date(year, 3, 31)
            elif quarter == 2:
                start_date = date(year, 4, 1)
                end_date = date(year, 6, 30)
            elif quarter == 3:
                start_date = date(year, 7, 1)
                end_date = date(year, 9, 30)
            else:  # quarter == 4
                start_date = date(year, 10, 1)
                end_date = date(year, 12, 31)
        else:
            # 月度: YYYY-MM
            year, month = map(int, period.split("-"))
            start_date = date(year, month, 1)

            # 计算月末日期
            if month == 12:
                end_date = date(year + 1, 1, 1) - timedelta(days=1)
            else:
                end_date = date(year, month + 1, 1) - timedelta(days=1)

        return start_date, end_date + timedelta(days=1)  # end_date 设为下一天0点，方便查询

    async def _generate_income_reconciliation(
        self, start_date: date, end_date: date
    ) -> dict:
        """生成收入对账"""
        from sqlalchemy import func
        from app.models.order import Order

        # 查询该周期内的应收
        result = await self.db.execute(
            select(Receivable)
            .join(Order)
            .where(
                and_(
                    Receivable.created_at >= datetime.combine(start_date, datetime.min.time()),
                    Receivable.created_at < datetime.combine(end_date, datetime.min.time()),
                )
            )
        )
        receivables = result.scalars().all()

        receivable_total = sum(Decimal(str(r.total_amount)) for r in receivables)
        received_total = sum(Decimal(str(r.received_amount)) for r in receivables)

        # 差异明细
        details = []
        for r in receivables:
            if r.received_amount < r.total_amount:
                order_result = await self.db.execute(
                    select(Order).where(Order.id == r.order_id)
                )
                order = order_result.scalar_one_or_none()
                details.append({
                    "order_id": r.order_id,
                    "order_no": order.order_no if order else "",
                    "receivable": str(r.total_amount),
                    "received": str(r.received_amount),
                    "difference": str(r.total_amount - r.received_amount),
                })

        return {
            "receivable_total": str(receivable_total),
            "received_total": str(received_total),
            "difference": str(receivable_total - received_total),
            "details": details,
        }

    async def _generate_expense_reconciliation(
        self, start_date: date, end_date: date
    ) -> dict:
        """生成支出对账（供应商付款）"""
        from app.models.supplier import Supplier

        # 查询该周期内的供应商付款
        result = await self.db.execute(
            select(Transaction)
            .join(Supplier, Transaction.supplier_id == Supplier.id, isouter=True)
            .where(
                and_(
                    Transaction.type == TransactionType.expense,
                    Transaction.category == ExpenseCategory.supplier_payment,
                    Transaction.date >= start_date,
                    Transaction.date < end_date,
                )
            )
        )
        transactions = result.scalars().all()

        paid_total = sum(Decimal(str(t.amount)) for t in transactions)

        # 按供应商分组
        by_supplier = {}
        for t in transactions:
            supplier_result = await self.db.execute(
                select(Supplier).where(Supplier.id == t.supplier_id)
            )
            supplier = supplier_result.scalar_one_or_none()

            supplier_name = supplier.name if supplier else "未知供应商"
            if supplier_name not in by_supplier:
                by_supplier[supplier_name] = Decimal("0")
            by_supplier[supplier_name] += Decimal(str(t.amount))

        details = [
            {
                "supplier_name": name,
                "amount": str(amount),
            }
            for name, amount in by_supplier.items()
        ]

        return {
            "paid_total": str(paid_total),
            "details": details,
        }
