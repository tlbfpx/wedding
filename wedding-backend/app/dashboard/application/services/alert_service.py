"""Alert service."""
from __future__ import annotations
from decimal import Decimal
from typing import Optional
from datetime import datetime, date, timedelta

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order, OrderStatus
from app.models.customer import Customer, CustomerStatus
from app.models.event import Event, EventStatus
from app.models.user import User
from app.dashboard.domain.value_objects import AlertLevel, PeriodRange
from app.dashboard.domain.dtos.alert_item import AlertItem
from app.dashboard.infrastructure.cache import RedisCacheService


class AlertService:
    """Service for risk alerts."""

    CACHE_TTL = 60

    @staticmethod
    def _get_cache_key(level, type_filter, scope, user_id) -> str:
        level_str = level.value if level else "all"
        type_str = type_filter or "all"
        return f"dashboard:alerts:{level_str}:{type_str}:{scope}:{user_id}"

    @staticmethod
    async def get_alerts(
        level: Optional[AlertLevel],
        type_filter: Optional[str],
        limit: int,
        offset: int,
        scope: str,
        user_id: int,
        db: AsyncSession
    ) -> tuple[int, list[AlertItem]]:
        """Get risk alerts."""
        cache_key = AlertService._get_cache_key(level, type_filter, scope, user_id)
        cached = await RedisCacheService.get(cache_key)
        if cached:
            # Return cached data
            alerts = [AlertItem(**a) for a in cached.get("alerts", [])]
            return cached.get("total", 0), alerts

        alerts = []

        # Check overdue receivables (HIGH)
        if level in (None, AlertLevel.HIGH):
            alerts.extend(await AlertService._check_overdue_receivables(scope, user_id, db))

        # Check upcoming events (MEDIUM)
        if level in (None, AlertLevel.HIGH, AlertLevel.MEDIUM):
            alerts.extend(await AlertService._check_upcoming_events(scope, user_id, db))

        # Check long no follow-up (MEDIUM)
        if level in (None, AlertLevel.HIGH, AlertLevel.MEDIUM):
            alerts.extend(await AlertService._check_long_no_follow(scope, user_id, db))

        # Sort by level (HIGH first) and created_at (newest first)
        level_order = {AlertLevel.HIGH: 0, AlertLevel.MEDIUM: 1, AlertLevel.LOW: 2}
        alerts.sort(key=lambda a: (level_order.get(a.level, 3), a.created_at), reverse=True)

        # Apply filters
        if level:
            alerts = [a for a in alerts if a.level == level]
        if type_filter:
            alerts = [a for a in alerts if a.type == type_filter]

        total = len(alerts)
        paginated = alerts[offset:offset + limit]

        # Cache result
        await RedisCacheService.set(
            cache_key,
            {"total": total, "alerts": [a.__dict__ for a in paginated]},
            AlertService.CACHE_TTL
        )

        return total, paginated

    @staticmethod
    async def _check_overdue_receivables(scope, user_id, db) -> list[AlertItem]:
        """Check for overdue receivables."""
        # Simplified: find orders with significant unpaid amounts
        query = select(Order).where(
            and_(
                Order.status.in_([OrderStatus.signed, OrderStatus.executing]),
                (Order.total_amount - Order.paid_amount) > 50000
            )
        ).limit(5)

        if scope == "own":
            query = query.where(Order.sale_id == user_id)

        result = await db.execute(query)
        orders = result.scalars().all()

        alerts = []
        for order in orders:
            overdue = order.total_amount - order.paid_amount
            alerts.append(AlertItem(
                id=f"alert_overdue_{order.id}",
                level=AlertLevel.HIGH,
                type="overdue_receivable",
                title=f"逾期应收：订单 {order.order_no}",
                detail=f"逾期金额 ¥{overdue:.0f}",
                entity_type="order",
                entity_id=order.id,
                owner_id=order.sale_id,
                owner_name=None,  # Would join with User
                actions=["view_detail", "mark_resolved"],
                created_at=datetime.utcnow()
            ))

        return alerts

    @staticmethod
    async def _check_upcoming_events(scope, user_id, db) -> list[AlertItem]:
        """Check for upcoming events not confirmed."""
        three_days_later = date.today() + timedelta(days=3)

        query = select(Event).where(
            and_(
                Event.date <= three_days_later,
                Event.date >= date.today(),
                Event.status.not_in([EventStatus.confirmed, EventStatus.cancelled])
            )
        ).limit(10)

        result = await db.execute(query)
        events = result.scalars().all()

        alerts = []
        for event in events:
            days_left = (event.date - date.today()).days
            alerts.append(AlertItem(
                id=f"alert_event_{event.id}",
                level=AlertLevel.MEDIUM,
                type="upcoming_event",
                title=f"即将到期：{event.title}",
                detail=f"{days_left}天后尚未确认最终方案",
                entity_type="event",
                entity_id=event.id,
                owner_id=event.planner_id,
                owner_name=None,
                actions=["view_detail", "send_remind"],
                created_at=datetime.utcnow()
            ))

        return alerts

    @staticmethod
    async def _check_long_no_follow(scope, user_id, db) -> list[AlertItem]:
        """Check for intention customers with no follow-up for 7+ days."""
        seven_days_ago = datetime.utcnow() - timedelta(days=7)

        query = select(Customer).where(
            and_(
                Customer.status == CustomerStatus.intention,
                Customer.created_at < seven_days_ago
            )
        ).limit(10)

        if scope == "own":
            query = query.where(Customer.assigned_sale_id == user_id)

        result = await db.execute(query)
        customers = result.scalars().all()

        alerts = []
        for customer in customers:
            alerts.append(AlertItem(
                id=f"alert_follow_{customer.id}",
                level=AlertLevel.MEDIUM,
                type="long_no_follow",
                title=f"长期未跟进：{customer.name}",
                detail="意向客户超过7天未跟进",
                entity_type="customer",
                entity_id=customer.id,
                owner_id=customer.assigned_sale_id,
                owner_name=None,
                actions=["view_detail", "assign_follow"],
                created_at=datetime.utcnow()
            ))

        return alerts

    @staticmethod
    async def mark_resolved(
        alert_id: str,
        note: str,
        user_id: int,
        db: AsyncSession
    ) -> bool:
        """Mark alert as resolved."""
        # In real implementation, this would:
        # 1. Check if alert exists and is active
        # 2. Record resolution in database
        # 3. Clear related cache

        # Extract entity type and id from alert_id
        # For now, just clear cache
        await RedisCacheService.delete_pattern("dashboard:alerts:*")
        return True
