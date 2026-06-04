"""Decision support metrics DTO."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional

from app.dashboard.domain.value_objects import PeriodType


@dataclass
class SourceROIMetric:
    """Customer source ROI metric."""
    source: str
    source_id: int
    lead_count: int
    signed_count: int
    conversion_rate: float
    revenue: Decimal
    avg_order_value: Decimal
    roi_score: int


@dataclass
class ServiceBreakdownMetric:
    """Service type breakdown metric."""
    service_type: str
    revenue: Decimal
    percent: float
    count: int


@dataclass
class SupplierValueMetric:
    """Supplier value metric."""
    supplier_id: int
    supplier_name: str
    type: str
    cooperation_count: int
    total_amount: Decimal
    avg_rating: float
    value_score: int


@dataclass
class DecisionSupportMetrics:
    """Decision support metrics."""
    period: PeriodType
    period_start: date
    period_end: date
    source_roi: list[SourceROIMetric]
    service_breakdown: list[ServiceBreakdownMetric]
    supplier_value: list[SupplierValueMetric]
