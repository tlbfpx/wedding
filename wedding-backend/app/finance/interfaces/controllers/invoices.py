"""
开票 API
"""
from __future__ import annotations
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import require_permission
from app.finance.application.services import InvoiceService
from app.finance.domain.entities.enums import InvoiceType, InvoiceStatus
from app.utils.pagination import PageResponse
import os

router = APIRouter()


class InvoiceCreate(BaseModel):
    """开票申请请求"""
    order_id: int
    invoice_type: InvoiceType
    amount: float
    title: str
    tax_no: str
    note: Optional[str] = None


class InvoiceUpdate(BaseModel):
    """开票状态更新请求"""
    status: Optional[InvoiceStatus] = None
    invoice_no: Optional[str] = None
    issued_at: Optional[datetime] = None


@router.post("")
async def create_invoice(
    data: InvoiceCreate,
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(require_permission("finance", "write")),
):
    """申请开票"""
    service = InvoiceService(db)
    invoice = await service.request_invoice(
        order_id=data.order_id,
        invoice_type=data.invoice_type,
        amount=data.amount,
        title=data.title,
        tax_no=data.tax_no,
        user_id=ctx["user"].id,
        note=data.note,
    )

    return {
        "id": invoice.id,
        "order_id": invoice.order_id,
        "invoice_type": invoice.invoice_type.value if isinstance(invoice.invoice_type, InvoiceType) else invoice.invoice_type,
        "amount": str(invoice.amount),
        "title": invoice.title,
        "tax_no": invoice.tax_no,
        "status": invoice.status.value if isinstance(invoice.status, InvoiceStatus) else invoice.status,
        "created_at": invoice.created_at.isoformat() if invoice.created_at else None,
    }


@router.get("")
async def list_invoices(
    order_id: Optional[int] = Query(None),
    status: Optional[InvoiceStatus] = Query(None),
    invoice_type: Optional[InvoiceType] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(require_permission("finance", "read")),
):
    """开票记录列表"""
    service = InvoiceService(db)
    items, total = await service.list_invoices(
        order_id=order_id,
        status=status,
        invoice_type=invoice_type,
        page=page,
        page_size=page_size,
    )

    result_items = []
    for item in items:
        result_items.append({
            "id": item.id,
            "order_id": item.order_id,
            "invoice_type": item.invoice_type.value if isinstance(item.invoice_type, InvoiceType) else item.invoice_type,
            "amount": str(item.amount),
            "title": item.title,
            "tax_no": item.tax_no,
            "status": item.status.value if isinstance(item.status, InvoiceStatus) else item.status,
            "invoice_no": item.invoice_no,
            "pdf_url": item.pdf_url,
            "issued_at": item.issued_at.isoformat() if item.issued_at else None,
            "created_at": item.created_at.isoformat() if item.created_at else None,
        })

    return PageResponse(
        items=result_items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/{invoice_id}")
async def get_invoice(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(require_permission("finance", "read")),
):
    """开票详情"""
    service = InvoiceService(db)
    invoice = await service.get_invoice(invoice_id)

    return {
        "id": invoice.id,
        "order_id": invoice.order_id,
        "invoice_type": invoice.invoice_type.value if isinstance(invoice.invoice_type, InvoiceType) else invoice.invoice_type,
        "amount": str(invoice.amount),
        "title": invoice.title,
        "tax_no": invoice.tax_no,
        "status": invoice.status.value if isinstance(invoice.status, InvoiceStatus) else invoice.status,
        "invoice_no": invoice.invoice_no,
        "pdf_url": invoice.pdf_url,
        "issued_at": invoice.issued_at.isoformat() if invoice.issued_at else None,
        "voided_at": invoice.voided_at.isoformat() if invoice.voided_at else None,
        "voided_by": invoice.voided_by,
        "note": invoice.note,
        "created_at": invoice.created_at.isoformat() if invoice.created_at else None,
        "created_by": invoice.created_by,
        "approval_id": invoice.approval_id,
    }


@router.put("/{invoice_id}")
async def update_invoice(
    invoice_id: int,
    data: InvoiceUpdate,
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(require_permission("finance", "write")),
):
    """更新开票状态/上传发票"""
    service = InvoiceService(db)
    invoice = await service.update_invoice(
        invoice_id=invoice_id,
        status=data.status,
        invoice_no=data.invoice_no,
        issued_at=data.issued_at,
    )

    return {
        "id": invoice.id,
        "status": invoice.status.value if isinstance(invoice.status, InvoiceStatus) else invoice.status,
        "invoice_no": invoice.invoice_no,
        "issued_at": invoice.issued_at.isoformat() if invoice.issued_at else None,
    }


@router.delete("/{invoice_id}")
async def void_invoice(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(require_permission("finance", "approve")),
):
    """作废发票"""
    service = InvoiceService(db)
    invoice = await service.void_invoice(invoice_id, ctx["user"].id)

    return {
        "id": invoice.id,
        "status": invoice.status.value if isinstance(invoice.status, InvoiceStatus) else invoice.status,
        "voided_at": invoice.voided_at.isoformat() if invoice.voided_at else None,
    }


@router.post("/{invoice_id}/upload")
async def upload_invoice_pdf(
    invoice_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(require_permission("finance", "write")),
):
    """上传发票 PDF"""
    from app.config import settings

    # 验证文件类型
    if file.content_type != "application/pdf":
        from app.utils.errors import AppException
        raise AppException(400, "INVALID_FILE_TYPE", "仅支持 PDF 文件")

    # 读取文件内容
    content = await file.read()

    # 验证大小
    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    if len(content) > max_bytes:
        from app.utils.errors import AppException
        raise AppException(400, "FILE_TOO_LARGE", f"文件大小不能超过{settings.MAX_FILE_SIZE_MB}MB")

    # 保存文件
    upload_dir = os.path.join(settings.UPLOAD_DIR, "invoices")
    os.makedirs(upload_dir, exist_ok=True)

    import re
    safe_filename = re.sub(r"[^\w.\-]", "_", file.filename)
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    file_name = f"{invoice_id}_{timestamp}_{safe_filename}"
    file_path = os.path.join(upload_dir, file_name)

    with open(file_path, "wb") as f:
        f.write(content)

    file_url = f"/uploads/invoices/{file_name}"

    # 更新发票记录
    service = InvoiceService(db)
    invoice = await service.upload_invoice_pdf(invoice_id, file_url)

    return {
        "id": invoice.id,
        "pdf_url": invoice.pdf_url,
        "uploaded_at": datetime.utcnow().isoformat(),
    }
