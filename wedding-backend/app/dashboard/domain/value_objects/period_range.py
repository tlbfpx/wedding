"""Period range value object for dashboard statistics."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, date
from enum import Enum
from typing import Optional


class PeriodType(str, Enum):
    """Statistics period type."""
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"


class CompareToType(str, Enum):
    """Comparison period type."""
    PREV_PERIOD = "prev_period"
    SAME_PERIOD_LAST_YEAR = "same_period_last_year"


@dataclass
class PeriodRange:
    """Time range for statistics."""
    period: PeriodType
    start: datetime
    end: datetime
    compare_start: Optional[datetime] = None
    compare_end: Optional[datetime] = None

    @classmethod
    def from_period(
        cls,
        period: PeriodType,
        compare_to: Optional[CompareToType] = None
    ) -> PeriodRange:
        """Create period range from period type.

        Args:
            period: Period type (month/quarter/year)
            compare_to: Comparison period type (optional)

        Returns:
            PeriodRange with start/end dates
        """
        now = datetime.utcnow()

        if period == PeriodType.MONTH:
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        elif period == PeriodType.QUARTER:
            quarter_month = ((now.month - 1) // 3) * 3 + 1
            start = now.replace(month=quarter_month, day=1, hour=0, minute=0, second=0, microsecond=0)
        else:  # YEAR
            start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)

        # Calculate comparison period
        compare_start = None
        compare_end = None

        if compare_to == CompareToType.PREV_PERIOD:
            if period == PeriodType.MONTH:
                # Previous month
                if start.month == 1:
                    compare_start = start.replace(year=start.year - 1, month=12, day=1)
                else:
                    compare_start = start.replace(month=start.month - 1, day=1)
                compare_end = start
            elif period == PeriodType.QUARTER:
                # Previous quarter
                if start.month <= 3:
                    compare_start = start.replace(year=start.year - 1, month=10, day=1)
                    compare_end = start.replace(month=1, day=1)
                else:
                    compare_start = start.replace(month=start.month - 3, day=1)
                    compare_end = start
            else:  # YEAR
                # Previous year
                compare_start = start.replace(year=start.year - 1)
                compare_end = start
        elif compare_to == CompareToType.SAME_PERIOD_LAST_YEAR:
            # Same period last year
            compare_start = start.replace(year=start.year - 1)
            compare_end = now.replace(year=now.year - 1)

        return cls(
            period=period,
            start=start,
            end=now,
            compare_start=compare_start,
            compare_end=compare_end
        )
