from __future__ import annotations

from fastapi import APIRouter, Depends, UploadFile, File, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.import_service import ImportService
from app.middleware.auth import get_current_user
from app.models.user import User
from app.utils.errors import AppException

router = APIRouter()


@router.get("/template")
async def download_template(
    import_type: str = Query(..., description="customer/supplier"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ImportService(db)
    return await service.get_template(import_type)


@router.post("/upload")
async def upload_import(
    import_type: str = Query(..., description="customer/supplier"),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ImportService(db)
    if import_type == "customer":
        return await service.import_customers(file)
    elif import_type == "supplier":
        return await service.import_suppliers(file)
    else:
        raise AppException(400, "INVALID_TYPE", f"不支持的导入类型: {import_type}")
