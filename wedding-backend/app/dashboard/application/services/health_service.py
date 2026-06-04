"""Health service for business health metrics."""
from __future__ import annotations
from decimal import Decimal
from typing import Optional

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order, OrderStatus
from app.models.customer import Customer, CustomerStatus
from app.models.payment import Payment, PaymentStatus

from app.dashboard.domain.value_objects import PeriodType, CompareToType, PeriodRange, MetricValue
from app.dashboard.domain.dtos import HealthMetrics, MetricValueResponse
from app.dashboard.infrastructure.cache import RedisCacheService


class HealthService:
    """Service for business health metrics."""

    CACHE_TTL = 300  # 5 minutes

    @staticmethod
    def _get_cache_key(
        period: PeriodType,
        compare_to: Optional[CompareToType],
        scope: str,
        user_id: int
    ) -> str:
        """Generate cache key for health metrics."""
        compare_str = compare_to.value if compare_to else "none"
        return f"dashboard:health:{period.value}:{compare_str}:{scope}:{user_id}"

    @staticmethod
    async def get_metrics(
        period: PeriodType,
        compare_to: Optional[CompareToType],
        scope: str,
        user_id: int,
        db: AsyncSession
    ) -> HealthMetrics:
        """Get business health metrics.

        Args:
            period: Statistics period
            compare_to: Comparison period type
            scope: Data scope (all/team/own)
            user_id: Current user ID
            db: Database session

        Returns:
            HealthMetrics with all metrics
        """
        # Check cache
        cache_key = HealthService._get_cache_key(period, compare_to, scope, user_id)
        cached = await RedisCacheService.get(cache_key)
        if cached:
            return HealthMetrics.model_validate(cached)

        # Calculate period range
        period_range = PeriodRange.from_period(period, compare_to)

        # Fetch metrics
        revenue = await HealthService._get_revenue(period_range, scope, user_id, db)
        orders_count = await HealthService._get_orders_count(period_range, scope, user_id, db)
        sign_rate = await HealthService._get_sign_rate(period_range, scope, user_id, db)
        gross_profit = await HealthService._get_gross_profit(period_range, scope, user_id, db)

        # Calculate average order value
        avg_order_value = Decimal("0")
        if orders_count.value > 0:
            avg_order_value = revenue.value / Decimal(orders_count.value)

        # Build metrics dict
        metrics = {
            "revenue": MetricValueResponse(
                value=float(revenue.value),
                trend=revenue.trend
            ),
            "orders": MetricValueResponse(
                value=float(orders_count.value)
            ),
            "avg_order_value": MetricValueResponse(
                value=float(avg_order_value)
            ),
            "sign_rate": MetricValueResponse(
                value=float(sign_rate.value)
            ),
            "gross_profit": MetricValueResponse(
                value=float(gross_profit.value),
                trend=gross_profit.trend
            ),
        }

        # Build response
        response = HealthMetrics(
            period=period,
            period_start=period_range.start.date(),
            period_end=period_range.end.date(),
            compare_period_start=period_range.compare_start.date() if period_range.compare_start else None,
            compare_period_end=period_range.compare_end.date() if period_range.compare_end else None,
            metrics=metrics
        )

        # Cache response
        await RedisCacheService.set(
            cache_key,
            response.model_dump(),
            HealthService.CACHE_TTL
        )

        return response

    @staticmethod
    async def _get_revenue(
        period_range: PeriodRange,
        scope: str,
        user_id: int,
        db: AsyncSession
    ) -> MetricValue:
        """Calculate total revenue."""
        # Current period
        query = select(func.sum(Order.total_amount)).where(
            and_(
                Order.created_at >= period_range.start,
                Order.created_at < period_range.end,
                Order.status.in_([OrderStatus.signed, OrderStatus.executing, OrderStatus.completed])
            )
        )

        # Apply scope filter
        query = HealthService._apply_scope_filter(query, Order.sale_id, scope, user_id)

        current_revenue = await db.scalar(query)
        current_value = Decimal(str(current_revenue)) if current_revenue else Decimal("0")

        # Comparison period (if available)
        trend = None
        if period_range.compare_start and period_range.compare_end:
            compare_query = select(func.sum(Order.total_amount)).where(
                and_(
                    Order.created_at >= period_range.compare_start,
                    Order.created_at < period_range.compare_end,
                    Order.status.in_([OrderStatus.signed, OrderStatus.executing, OrderStatus.completed])
                )
            )
            compare_query = HealthService._apply_scope_filter(compare_query, Order.sale_id, scope, user_id)

            compare_revenue = await db.scalar(compare_query)
            compare_value = Decimal(str(compare_revenue)) if compare_revenue else Decimal("0")

            if compare_value > 0:
                trend = float((current_value - compare_value) / compare_value)

        return MetricValue(value=current_value, trend=trend)

    @staticmethod
    async def _get_orders_count(
        period_range: PeriodRange,
        scope: str,
        user_id: int,
        db: AsyncSession
    ) -> MetricValue:
        """Calculate order count."""
        query = select(func.count(Order.id)).where(
            and_(
                Order.created_at >= period_range.start,
                Order.created_at < period_range.end,
                Order.status.in_([OrderStatus.signed, OrderStatus.executing, OrderStatus.completed])
            )
        )

        query = HealthService._apply_scope_filter(query, Order.sale_id, scope, user_id)

        count = await db.scalar(query)
        value = int(count) if count else 0

        return MetricValue(value=Decimal(value))

    @staticmethod
    async def _get_sign_rate(
        period_range: PeriodRange,
        scope: str,
        user_id: int,
        db: AsyncSession
    ) -> MetricValue:
        """Calculate sign rate (signed customers / total customers in funnel)."""
        query = select(
            func.count(Customer.id).filter(Customer.status == CustomerStatus.signed),
            func.count(Customer.id)
        ).where(
            and_(
                Customer.created_at >= period_range.start,
                Customer.created_at < period_range.end,
                Customer.status.in_([CustomerStatus.signed, CustomerStatus.intention, CustomerStatus.lost])
            )
        )

        query = HealthService._apply_scope_filter(query, Customer.assigned_sale_id, scope, user_id)

        signed_count, total_count = await db.execute(query).one() or (0, 0)

        rate = 0.0
        if total_count > 0:
            rate = float(signed_count) / float(total_count)

        return MetricValue(value=Decimal(str(rate)))

    @staticmethod
    async def _get_gross_profit(
        period_range: PeriodRange,
        scope: str,
        user_id: int,
        db: AsyncSession
    ) -> MetricValue:
        """Calculate gross profit (revenue - supplier payments)."""
        # For simplicity, gross_profit = revenue * 0.35 (assumed margin)
        # In real implementation, this would sum up actual supplier payments
        revenue = await HealthService._get_revenue(period_range, scope, user_id, db)
        gross_profit = revenue.value * Decimal("0.35")

        return MetricValue(value=gross_profit, trend=revenue.trend)

    @staticmethod
    def _apply_scope_filter(query, column, scope: str, user_id: int):
        """Apply scope filter to query.

        Args:
            query: SQLAlchemy query
            column: Column to filter on (e.g., Order.sale_id)
            scope: Data scope (all/team/own)
            user_id: Current user ID

        Returns:
            Filtered query
        """
        if scope == "own":
            return query.where(column == user_id)
        # For "all" and "team", we'd need to join with User table to get team info
        # Simplified here - just return query as-is for "all"
        return query
