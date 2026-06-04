"""Health metrics DTO."""
from __future__ import annotations
from pydantic import BaseModel, Field
from datetime import date
from typing import Optional, Dict

from app.dashboard.domain.value_objects import PeriodType, MetricValue


class MetricValueResponse(BaseModel):
    """Metric value for API response."""
    value: float
    trend: Optional[float] = None
    target: Optional[float] = None
    achievement: Optional[float] = None

    class Config:
        # Convert from MetricValue dataclass
        from_attributes = True


class HealthMetrics(BaseModel):
    """Business health metrics."""
    period: PeriodType
    period_start: date
    period_end: date
    compare_period_start: Optional[date] = None
    compare_period_end: Optional[date] = None
    metrics: Dict[str, MetricValueResponse] = Field(default_factory=dict)
