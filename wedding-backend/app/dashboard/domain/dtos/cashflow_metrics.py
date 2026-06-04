"""Cashflow metrics DTO."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional


@dataclass
class CashInBreakdown:
    """Cash in breakdown by payment method."""
    total: Decimal
    by_method: dict[str, Decimal]


@dataclass
class ReceivablesSummary:
    """Receivables summary."""
    total: Decimal
    overdue: Decimal
    overdue_count: int


@dataclass
class AgingBucket:
    """Aging bucket."""
    bucket: str
    amount: Decimal
    percent: float


@dataclass
class PaymentSummary:
    """Payment summary."""
    total: Decimal
    paid: Decimal
    pending: Decimal


@dataclass
class CashflowMetrics:
    """Cashflow metrics."""
    period: PeriodType
    period_start: date
    period_end: date
    cash_in: CashInBreakdown
    receivables: ReceivablesSummary
    aging: list[AgingBucket]
    turnover_days: int
    payments: PaymentSummary
