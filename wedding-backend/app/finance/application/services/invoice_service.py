"""
开票服务
"""
from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.finance.infrastructure.repositories import InvoiceRepository
from app.finance.domain.entities import Invoice
from app.finance.domain.entities.enums import InvoiceType, InvoiceStatus
from app.events import DomainEvent, event_bus
from app.events.event_types import APPROVAL_CREATED
from app.utils.errors import AppException
from app.config import settings


class InvoiceService:
    """开票服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.invoice_repo = InvoiceRepository(db)

    async def request_invoice(
        self,
        order_id: int,
        invoice_type: InvoiceType,
        amount: float,
        title: str,
        tax_no: str,
        user_id: int,
        note: Optional[str] = None,
    ) -> Invoice:
        """申请开票

        Args:
            order_id: 订单ID
            invoice_type: 发票类型
            amount: 开票金额
            title: 发票抬头
            tax_no: 税号
            user_id: 申请人ID
            note: 备注

        Returns:
            Invoice: 开票记录

        Raises:
            AppException: 开票金额超过订单总额
        """
        # 校验金额
        from app.models.order import Order

        order_result = await self.db.execute(
            select(Order).where(Order.id == order_id)
        )
        order = order_result.scalar_one_or_none()
        if not order:
            raise AppException(404, "ORDER_NOT_FOUND", "订单不存在")

        if Decimal(str(amount)) > Decimal(str(order.total_amount)):
            raise AppException(400, "INVOICE_AMOUNT_EXCEEDS", "开票金额超过订单总额")

        # 检查是否需要审批（超过阈值）
        approval_id = None
        threshold = Decimal(str(getattr(settings, "INVOICE_APPROVAL_THRESHOLD", 50000)))
        if Decimal(str(amount)) > threshold:
            from app.models.order import Approval, ApprovalType, ApprovalStatus

            approval = Approval(
                type=ApprovalType.discount,  # 临时使用 discount，需要添加 invoice 类型
                target_id=0,  # 稍后填充
                applicant_id=user_id,
                reason=f"开票申请 {title} ({invoice_type.value})",
                status=ApprovalStatus.pending,
            )
            self.db.add(approval)
            await self.db.flush()
            approval_id = approval.id

        # 创建开票记录
        invoice = await self.invoice_repo.create(
            order_id=order_id,
            invoice_type=invoice_type,
            amount=amount,
            title=title,
            tax_no=tax_no,
            created_by=user_id,
            note=note,
        )

        if approval_id:
            invoice.approval_id = approval_id
            invoice.status = InvoiceStatus.processing
            # 更新 approval 的 target_id
            from app.models.order import Approval
            approval_result = await self.db.execute(
                select(Approval).where(Approval.id == approval_id)
            )
            approval = approval_result.scalar_one_or_none()
            if approval:
                approval.target_id = invoice.id
            await self.invoice_repo.update(invoice)

        await self.db.commit()
        await self.db.refresh(invoice)

        # 发布事件
        from app.finance.domain.events.event_types import INVOICE_REQUESTED
        await event_bus.publish(DomainEvent(
            event_type=INVOICE_REQUESTED,
            payload={
                "invoice_id": invoice.id,
                "order_id": order_id,
                "amount": str(amount),
                "invoice_type": invoice_type.value,
            }
        ))

        return invoice

    async def update_invoice(
        self,
        invoice_id: int,
        status: Optional[InvoiceStatus] = None,
        invoice_no: Optional[str] = None,
        issued_at: Optional[datetime] = None,
    ) -> Invoice:
        """更新开票状态"""
        invoice = await self.invoice_repo.get(invoice_id)
        if not invoice:
            raise AppException(404, "INVOICE_NOT_FOUND", "开票记录不存在")

        # 检查发票号码唯一性
        if invoice_no:
            existing = await self.invoice_repo.get_by_invoice_no(invoice_no)
            if existing and existing.id != invoice_id:
                raise AppException(400, "INVOICE_NO_EXISTS", "发票号码已存在")
            invoice.invoice_no = invoice_no

        if status:
            invoice.status = status

        if issued_at:
            invoice.issued_at = issued_at

        invoice = await self.invoice_repo.update(invoice)

        await self.db.commit()
        await self.db.refresh(invoice)

        # 如果状态变更为已开票，发布事件
        if status == InvoiceStatus.issued:
            from app.finance.domain.events.event_types import INVOICE_ISSUED
            await event_bus.publish(DomainEvent(
                event_type=INVOICE_ISSUED,
                payload={
                    "invoice_id": invoice.id,
                    "order_id": invoice.order_id,
                    "invoice_no": invoice.invoice_no,
                    "issued_at": invoice.issued_at.isoformat() if invoice.issued_at else None,
                }
            ))

        return invoice

    async def void_invoice(self, invoice_id: int, user_id: int) -> Invoice:
        """作废发票"""
        invoice = await self.invoice_repo.get(invoice_id)
        if not invoice:
            raise AppException(404, "INVOICE_NOT_FOUND", "开票记录不存在")

        if invoice.status == InvoiceStatus.voided:
            raise AppException(400, "ALREADY_VOIDED", "发票已作废")

        invoice.status = InvoiceStatus.voided
        invoice.voided_at = datetime.utcnow()
        invoice.voided_by = user_id
        await self.invoice_repo.update(invoice)

        # 发布事件
        from app.finance.domain.events.event_types import INVOICE_VOIDED
        await event_bus.publish(DomainEvent(
            event_type=INVOICE_VOIDED,
            payload={
                "invoice_id": invoice.id,
                "order_id": invoice.order_id,
            }
        ))

        return invoice

    async def upload_invoice_pdf(
        self, invoice_id: int, pdf_url: str
    ) -> Invoice:
        """上传发票 PDF"""
        invoice = await self.invoice_repo.get(invoice_id)
        if not invoice:
            raise AppException(404, "INVOICE_NOT_FOUND", "开票记录不存在")

        invoice.pdf_url = pdf_url
        return await self.invoice_repo.update(invoice)

    async def get_invoice(self, invoice_id: int) -> Invoice:
        """获取开票记录"""
        invoice = await self.invoice_repo.get(invoice_id)
        if not invoice:
            raise AppException(404, "INVOICE_NOT_FOUND", "开票记录不存在")
        return invoice

    async def list_invoices(
        self,
        order_id: Optional[int] = None,
        status: Optional[InvoiceStatus] = None,
        invoice_type: Optional[InvoiceType] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Invoice], int]:
        """查询开票列表"""
        offset = (page - 1) * page_size
        return await self.invoice_repo.list(
            order_id=order_id,
            status=status,
            invoice_type=invoice_type,
            offset=offset,
            limit=page_size,
        )
