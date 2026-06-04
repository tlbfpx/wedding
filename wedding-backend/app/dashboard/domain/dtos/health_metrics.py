"""Health metrics DTO."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from typing import Optional

from app.dashboard.domain.value_objects import PeriodType, MetricValue


@dataclass
class HealthMetrics:
    """Business health metrics."""
    period: PeriodType
    period_start: date
    period_end: date
    compare_period_start: Optional[date] = None
    compare_period_end: Optional[date] = None
    metrics: dict[str, MetricValue] = None

    def __post_init__(self):
        if self.metrics is None:
            self.metrics = {}
