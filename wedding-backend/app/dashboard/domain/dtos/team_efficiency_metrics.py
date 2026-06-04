"""Team efficiency metrics DTO."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional

from app.dashboard.domain.value_objects import PeriodType


@dataclass
class TeamStats:
    """Team statistics."""
    team: str
    total_revenue: Decimal
    headcount: int
    avg_revenue: Decimal


@dataclass
class FunnelStage:
    """Conversion funnel stage."""
    stage: str
    count: int
    rate: float


@dataclass
class SalesRankingItem:
    """Sales ranking item."""
    rank: int
    sale_id: int
    sale_name: str
    team: str
    order_count: int
    revenue: Decimal
    avg_order_value: Decimal
    conversion_rate: float
    follow_up_count: int


@dataclass
class TeamEfficiencyMetrics:
    """Team efficiency metrics."""
    period: PeriodType
    period_start: date
    period_end: date
    teams: list[TeamStats]
    funnel: list[FunnelStage]
    new_customers: int
    follow_up_count: int
    ranking: list[SalesRankingItem]
    total: int
    page: int
    page_size: int
