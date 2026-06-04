"""Metric value with trend analysis."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from decimal import Decimal


@dataclass
class MetricValue:
    """Metric value with trend and target."""
    value: Decimal
    trend: Optional[float] = None  # Growth rate (e.g., 0.125 = +12.5%)
    target: Optional[Decimal] = None  # Target value
    achievement: Optional[float] = None  # Achievement rate (0-1)
