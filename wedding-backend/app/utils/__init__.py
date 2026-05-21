from app.utils.errors import AppException
from fastapi import HTTPException


def check_optimistic_lock(db_updated_at, request_updated_at):
    if db_updated_at and request_updated_at and db_updated_at != request_updated_at:
        raise AppException(409, "CONCURRENT_MODIFICATION", "数据已被其他用户修改，请刷新后重试")
