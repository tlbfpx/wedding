from fastapi import HTTPException
from pydantic import BaseModel


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: str | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


class AppException(HTTPException):
    def __init__(self, status_code: int, code: str, message: str, details: str | None = None):
        self.error = ErrorDetail(code=code, message=message, details=details)
        super().__init__(status_code=status_code, detail=self.error.model_dump())
