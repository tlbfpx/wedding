"""
开票数据访问层
"""
from __future__ import annotations
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.finance.domain.entities import Invoice
from app.finance.domain.entities.enums import InvoiceStatus, InvoiceType


class InvoiceRepository:
    """开票 Repository"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, invoice_id: int) -> Optional[Invoice]:
        """根据ID获取开票记录"""
        result = await self.db.execute(
            select(Invoice).where(Invoice.id == invoice_id)
        )
        return result.scalar_one_or_none()

    async def get_by_invoice_no(self, invoice_no: str) -> Optional[Invoice]:
        """根据发票号码获取开票记录"""
        result = await self.db.execute(
            select(Invoice).where(Invoice.invoice_no == invoice_no)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        order_id: int,
        invoice_type: InvoiceType,
        amount: float,
        title: str,
        tax_no: str,
        created_by: int,
        note: Optional[str] = None,
    ) -> Invoice:
        """创建开票记录"""
        invoice = Invoice(
            order_id=order_id,
            invoice_type=invoice_type,
            amount=amount,
            title=title,
            tax_no=tax_no,
            status=InvoiceStatus.pending,
            note=note,
            created_by=created_by,
        )
        self.db.add(invoice)
        await self.db.flush()
        await self.db.refresh(invoice)
        return invoice

    async def update(self, invoice: Invoice) -> Invoice:
        """更新开票记录"""
        await self.db.flush()
        await self.db.refresh(invoice)
        return invoice

    async def delete(self, invoice_id: int) -> None:
        """删除开票记录"""
        invoice = await self.get(invoice_id)
        if invoice:
            await self.db.delete(invoice)

    async def list(
        self,
        order_id: Optional[int] = None,
        status: Optional[InvoiceStatus] = None,
        invoice_type: Optional[InvoiceType] = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Invoice], int]:
        """查询开票列表"""
        from sqlalchemy import func

        query = select(Invoice)

        if order_id:
            query = query.where(Invoice.order_id == order_id)

        if status:
            query = query.where(Invoice.status == status)

        if invoice_type:
            query = query.where(Invoice.invoice_type == invoice_type)

        # Count total
        count_result = await self.db.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar_one()

        # Fetch with pagination
        query = query.order_by(Invoice.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(query)
        items = result.scalars().all()

        return list(items), total

    async def get_with_details(self, invoice_id: int) -> Optional[Invoice]:
        """获取开票详情（包含关联订单）"""
        result = await self.db.execute(
            select(Invoice)
            .options(selectinload(Invoice.order))
            .where(Invoice.id == invoice_id)
        )
        return result.scalar_one_or_none()
