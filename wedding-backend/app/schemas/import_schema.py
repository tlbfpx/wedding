from pydantic import BaseModel
from typing import Optional
from enum import Enum


class ImportType(str, Enum):
    customer = "customer"
    supplier = "supplier"


class ImportResult(BaseModel):
    total: int
    success: int
    failed: int
    errors: list[dict]


class ImportError(BaseModel):
    row: int
    field: str
    message: str
