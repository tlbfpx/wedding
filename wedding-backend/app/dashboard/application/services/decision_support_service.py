"""Decision support service."""
from __future__ import annotations
from decimal import Decimal
from typing import Optional

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order, OrderStatus, OrderItem
from app.models.customer import Customer, CustomerSource
from app.models.supplier import Supplier
from app.dashboard.domain.value_objects import PeriodType, PeriodRange, DecisionDimension
from app.dashboard.infrastructure.cache import RedisCacheService


class DecisionSupportService:
    """Service for decision support metrics."""

    CACHE_TTL = 600

    @staticmethod
    def _get_cache_key(period, dimension, scope) -> str:
        return f"dashboard:decision:{period.value}:{dimension.value}:{scope}"

    @staticmethod
    async def get_metrics(
        period: PeriodType,
        dimension: DecisionDimension,
        scope: str,
        user_id: int,
        db: AsyncSession
    ) -> dict:
        """Get decision support metrics."""
        cache_key = DecisionSupportService._get_cache_key(period, dimension, scope)
        cached = await RedisCacheService.get(cache_key)
        if cached:
            return cached

        period_range = PeriodRange.from_period(period)

        response = {
            "period": period.value,
            "period_start": period_range.start.date(),
            "period_end": period_range.end.date(),
            "source_roi": [],
            "service_breakdown": [],
            "supplier_value": []
        }

        # Get source ROI
        if dimension in (DecisionDimension.SOURCE, DecisionDimension.ALL):
            response["source_roi"] = await DecisionSupportService._get_source_roi(period_range, scope, user_id, db)

        # Get service breakdown
        if dimension in (DecisionDimension.SERVICE, DecisionDimension.ALL):
            response["service_breakdown"] = await DecisionSupportService._get_service_breakdown(period_range, scope, user_id, db)

        # Get supplier value
        if dimension in (DecisionDimension.SUPPLIER, DecisionDimension.ALL):
            response["supplier_value"] = await DecisionSupportService._get_supplier_value(period_range, scope, user_id, db)

        await RedisCacheService.set(cache_key, response, DecisionSupportService.CACHE_TTL)
        return response

    @staticmethod
    async def _get_source_roi(period_range, scope, user_id, db) -> list:
        """Get customer source ROI analysis."""
        query = select(
            CustomerSource.id.label("source_id"),
            CustomerSource.name.label("source"),
            func.count(Customer.id).label("lead_count"),
            func.count(func.filter(Customer.status == CustomerStatus.signed, Customer.id)).label("signed_count"),
            func.coalesce(func.sum(Order.total_amount), 0).label("revenue")
        ).outerjoin(
            Customer, Customer.source_id == CustomerSource.id
        ).outerjoin(
            Order, and_(
                Order.customer_id == Customer.id,
                Order.created_at >= period_range.start,
                Order.created_at < period_range.end,
                Order.status.in_([OrderStatus.signed, OrderStatus.executing, OrderStatus.completed])
            )
        ).where(
            Customer.created_at >= period_range.start
        ).group_by(CustomerSource.id, CustomerSource.name)

        result = await db.execute(query)

        source_roi = []
        for row in result.all():
            lead_count = row.lead_count or 0
            signed_count = row.signed_count or 0
            revenue = Decimal(str(row.revenue)) if row.revenue else Decimal("0")

            conversion_rate = signed_count / lead_count if lead_count > 0 else 0
            avg_order_value = revenue / signed_count if signed_count > 0 else Decimal("0")

            # Calculate ROI score (1-5)
            roi_score = DecisionSupportService._calculate_roi_score(lead_count, conversion_rate, avg_order_value)

            source_roi.append({
                "source": row.source,
                "source_id": row.source_id,
                "lead_count": lead_count,
                "signed_count": signed_count,
                "conversion_rate": conversion_rate,
                "revenue": float(revenue),
                "avg_order_value": float(avg_order_value),
                "roi_score": roi_score
            })

        # Sort by revenue
        source_roi.sort(key=lambda x: x["revenue"], reverse=True)
        return source_roi

    @staticmethod
    def _calculate_roi_score(lead_count, conversion_rate, avg_order_value) -> int:
        """Calculate ROI score (1-5 stars)."""
        score = 1

        # Conversion rate weight 40%
        if conversion_rate >= 0.7:
            score += 2
        elif conversion_rate >= 0.5:
            score += 1

        # Lead count weight 30%
        if lead_count >= 40:
            score += 2
        elif lead_count >= 20:
            score += 1

        # Average order value weight 30%
        if float(avg_order_value) >= 30000:
            score += 1
        elif float(avg_order_value) >= 25000:
            score += 0.5

        return min(5, int(score))

    @staticmethod
    async def _get_service_breakdown(period_range, scope, user_id, db) -> list:
        """Get service type revenue breakdown."""
        query = select(
            OrderItem.type.label("service_type"),
            func.sum(OrderItem.amount).label("revenue"),
            func.count(func.distinct(OrderItem.order_id)).label("count")
        ).join(
            Order, and_(
                Order.id == OrderItem.order_id,
                Order.created_at >= period_range.start,
                Order.created_at < period_range.end,
                Order.status.in_([OrderStatus.signed, OrderStatus.executing, OrderStatus.completed])
            )
        ).group_by(OrderItem.type).order_by(
            func.sum(OrderItem.amount).desc()
        )

        result = await db.execute(query)

        service_breakdown = []
        total_revenue = Decimal("0")

        for row in result.all():
            revenue = Decimal(str(row.revenue)) if row.revenue else Decimal("0")
            total_revenue += revenue

        # Second pass to calculate percentages
        result = await db.execute(query)
        for row in result.all():
            revenue = Decimal(str(row.revenue)) if row.revenue else Decimal("0")
            percent = float(revenue / total_revenue) if total_revenue > 0 else 0

            service_breakdown.append({
                "service_type": row.service_type.value,
                "revenue": float(revenue),
                "percent": percent,
                "count": row.count or 0
            })

        return service_breakdown

    @staticmethod
    async def _get_supplier_value(period_range, scope, user_id, db) -> list:
        """Get supplier value analysis."""
        query = select(
            Supplier.id.label("supplier_id"),
            Supplier.name.label("supplier_name"),
            Supplier.type,
            func.count(func.distinct(OrderItem.order_id)).label("cooperation_count"),
            func.sum(OrderItem.amount).label("total_amount")
        ).join(
            OrderItem, OrderItem.supplier_id == Supplier.id
        ).join(
            Order, and_(
                Order.id == OrderItem.order_id,
                Order.created_at >= period_range.start,
                Order.created_at < period_range.end
            )
        ).group_by(Supplier.id, Supplier.name, Supplier.type)

        result = await db.execute(query)

        supplier_value = []
        for row in result.all():
            total_amount = Decimal(str(row.total_amount)) if row.total_amount else Decimal("0")
            cooperation_count = row.cooperation_count or 0

            # Simplified: assume avg rating 4.0
            avg_rating = 4.0

            value_score = DecisionSupportService._calculate_value_score(cooperation_count, avg_rating, total_amount)

            supplier_value.append({
                "supplier_id": row.supplier_id,
                "supplier_name": row.supplier_name,
                "type": row.type.value if row.type else "other",
                "cooperation_count": cooperation_count,
                "total_amount": float(total_amount),
                "avg_rating": avg_rating,
                "value_score": value_score
            })

        # Sort by cooperation count
        supplier_value.sort(key=lambda x: x["cooperation_count"], reverse=True)
        return supplier_value

    @staticmethod
    def _calculate_value_score(cooperation_count, avg_rating, total_amount) -> int:
        """Calculate supplier value score (1-5)."""
        score = 1

        # Rating weight 50%
        if avg_rating >= 4.5:
            score += 2.5
        elif avg_rating >= 4.0:
            score += 2
        elif avg_rating >= 3.5:
            score += 1

        # Cooperation count weight 30%
        if cooperation_count >= 10:
            score += 1.5
        elif cooperation_count >= 5:
            score += 1

        # Total amount weight 20%
        if float(total_amount) >= 100000:
            score += 1
        elif float(total_amount) >= 50000:
            score += 0.5

        return min(5, int(score))
