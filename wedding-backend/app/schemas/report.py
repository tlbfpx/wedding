from pydantic import BaseModel
from typing import Optional
from enum import Enum


class ReportType(str, Enum):
    order = "order"
    customer = "customer"
    finance = "finance"


class ReportExportQuery(BaseModel):
    report_type: ReportType
    date_start: Optional[str] = None
    date_end: Optional[str] = None
    status: Optional[str] = None
    sale_id: Optional[int] = None
