from typing import TypeVar, Generic
from pydantic import BaseModel

T = TypeVar("T")


class PageParams(BaseModel):
    page: int = 1
    page_size: int = 20
    sort_by: str = "created_at"
    sort_order: str = "desc"


class PageResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int
