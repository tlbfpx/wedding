from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_db
from app.services.report_service import ReportService
from app.middleware.auth import require_permission
from app.utils.errors import AppException

router = APIRouter()


@router.get("/export")
async def export_report(
    report_type: str = Query(..., description="order/customer/finance"),
    date_start: Optional[str] = Query(None),
    date_end: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    sale_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    ctx: dict = Depends(require_permission("report", "read")),
):
    service = ReportService(db)
    if report_type == "order":
        return await service.export_orders(date_start, date_end, status, sale_id)
    elif report_type == "customer":
        return await service.export_customers(date_start, date_end, status, sale_id)
    elif report_type == "finance":
        return await service.export_finance(date_start, date_end, sale_id)
    else:
        raise AppException(400, "INVALID_TYPE", f"不支持的报表类型: {report_type}")
