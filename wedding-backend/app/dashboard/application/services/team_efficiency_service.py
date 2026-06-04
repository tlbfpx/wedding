"""Team efficiency service."""
from __future__ import annotations
from decimal import Decimal
from typing import Optional

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order, OrderStatus
from app.models.customer import Customer, CustomerStatus
from app.models.customer import FollowUp
from app.models.user import User
from app.dashboard.domain.value_objects import PeriodType, PeriodRange
from app.dashboard.infrastructure.cache import RedisCacheService


class TeamEfficiencyService:
    """Service for team efficiency metrics."""

    CACHE_TTL = 300

    @staticmethod
    def _get_cache_key(period, team, page, page_size, scope, user_id) -> str:
        team_str = team or "all"
        return f"dashboard:team:{period.value}:{team_str}:{page}:{page_size}:{scope}:{user_id}"

    @staticmethod
    async def get_metrics(
        period: PeriodType,
        team: Optional[str],
        page: int,
        page_size: int,
        scope: str,
        user_id: int,
        db: AsyncSession
    ) -> dict:
        """Get team efficiency metrics."""
        cache_key = TeamEfficiencyService._get_cache_key(period, team, page, page_size, scope, user_id)
        cached = await RedisCacheService.get(cache_key)
        if cached:
            return cached

        period_range = PeriodRange.from_period(period)

        # Get team stats
        teams = await TeamEfficiencyService._get_team_stats(period_range, scope, user_id, db)

        # Get conversion funnel
        funnel = await TeamEfficiencyService._get_funnel(period_range, scope, user_id, db)

        # Get new customers
        new_customers = await TeamEfficiencyService._get_new_customers(period_range, scope, user_id, db)

        # Get follow up count
        follow_up_count = await TeamEfficiencyService._get_follow_up_count(period_range, scope, user_id, db)

        # Get sales ranking
        ranking, total = await TeamEfficiencyService._get_sales_ranking(
            period_range, team, page, page_size, scope, user_id, db
        )

        response = {
            "period": period.value,
            "period_start": period_range.start.date(),
            "period_end": period_range.end.date(),
            "teams": [
                {
                    "team": t.team,
                    "total_revenue": float(t.total_revenue),
                    "headcount": t.headcount,
                    "avg_revenue": float(t.avg_revenue)
                }
                for t in teams
            ],
            "funnel": [
                {"stage": f.stage, "count": f.count, "rate": f.rate}
                for f in funnel
            ],
            "new_customers": new_customers,
            "follow_up_count": follow_up_count,
            "ranking": [
                {
                    "rank": r.rank,
                    "sale_id": r.sale_id,
                    "sale_name": r.sale_name,
                    "team": r.team,
                    "order_count": r.order_count,
                    "revenue": float(r.revenue),
                    "avg_order_value": float(r.avg_order_value),
                    "conversion_rate": r.conversion_rate,
                    "follow_up_count": r.follow_up_count
                }
                for r in ranking
            ],
            "total": total,
            "page": page,
            "page_size": page_size
        }

        await RedisCacheService.set(cache_key, response, TeamEfficiencyService.CACHE_TTL)
        return response

    @staticmethod
    async def _get_team_stats(period_range, scope, user_id, db) -> list:
        """Get team statistics."""
        query = select(
            User.team,
            func.count(User.id).label("headcount"),
            func.sum(Order.total_amount).label("total_revenue")
        ).join(Order, Order.sale_id == User.id).where(
            and_(
                Order.created_at >= period_range.start,
                Order.created_at < period_range.end,
                Order.status.in_([OrderStatus.signed, OrderStatus.executing, OrderStatus.completed])
            )
        ).group_by(User.team)

        if scope == "own":
            query = query.where(User.id == user_id)

        result = await db.execute(query)

        teams = []
        for row in result.all():
            headcount = row.headcount or 1
            total_revenue = Decimal(str(row.total_revenue)) if row.total_revenue else Decimal("0")
            teams.append(type('TeamStat', (), {
                'team': row.team,
                'total_revenue': total_revenue,
                'headcount': headcount,
                'avg_revenue': total_revenue / headcount
            })())

        return teams

    @staticmethod
    async def _get_funnel(period_range, scope, user_id, db) -> list:
        """Get conversion funnel."""
        query = select(
            Customer.status,
            func.count(Customer.id)
        ).where(
            Customer.created_at >= period_range.start
        ).group_by(Customer.status)

        if scope == "own":
            query = query.where(Customer.assigned_sale_id == user_id)

        result = await db.execute(query)
        counts = {row[0].value: row[1] for row in result.all()}

        funnel_order = ["potential", "following", "intention", "signed", "lost"]
        total = sum(counts.get(s, 0) for s in funnel_order) or 1

        funnel = []
        for stage in funnel_order:
            count = counts.get(stage, 0)
            rate = count / total
            funnel.append(type('FunnelStage', (), {
                'stage': stage,
                'count': count,
                'rate': rate
            })())

        return funnel

    @staticmethod
    async def _get_new_customers(period_range, scope, user_id, db) -> int:
        """Get new customers count."""
        query = select(func.count(Customer.id)).where(
            Customer.created_at >= period_range.start
        )

        if scope == "own":
            query = query.where(Customer.assigned_sale_id == user_id)

        count = await db.scalar(query)
        return int(count) if count else 0

    @staticmethod
    async def _get_follow_up_count(period_range, scope, user_id, db) -> int:
        """Get follow up count."""
        query = select(func.count(FollowUp.id)).where(
            FollowUp.created_at >= period_range.start
        )

        if scope == "own":
            query = query.where(FollowUp.sale_id == user_id)

        count = await db.scalar(query)
        return int(count) if count else 0

    @staticmethod
    async def _get_sales_ranking(period_range, team, page, page_size, scope, user_id, db) -> tuple:
        """Get sales ranking."""
        query = select(
            User.id.label("sale_id"),
            User.name.label("sale_name"),
            User.team,
            func.count(Order.id).label("order_count"),
            func.sum(Order.total_amount).label("total_revenue")
        ).join(Order, Order.sale_id == User.id).where(
            and_(
                Order.created_at >= period_range.start,
                Order.created_at < period_range.end,
                Order.status.in_([OrderStatus.signed, OrderStatus.executing, OrderStatus.completed])
            )
        ).group_by(User.id, User.name, User.team).order_by(
            func.sum(Order.total_amount).desc()
        )

        if team:
            query = query.where(User.team == team)

        if scope == "own":
            query = query.where(User.id == user_id)

        # Get total count
        count_query = query.alias()
        total_result = await db.execute(select(func.count()).select_from(count_query))
        total = total_result.scalar() or 0

        # Apply pagination
        offset = (page - 1) * page_size
        query = query.limit(page_size).offset(offset)

        result = await db.execute(query)

        ranking = []
        rank = offset + 1
        for row in result.all():
            order_count = row.order_count or 0
            total_rev = Decimal(str(row.total_revenue)) if row.total_revenue else Decimal("0")
            avg_order = total_rev / order_count if order_count > 0 else Decimal("0")

            # Get conversion rate
            signed_query = select(func.count(Customer.id)).where(
                and_(
                    Customer.assigned_sale_id == row.sale_id,
                    Customer.status == CustomerStatus.signed
                )
            )
            signed = await db.scalar(signed_query) or 0

            total_query = select(func.count(Customer.id)).where(
                Customer.assigned_sale_id == row.sale_id
            )
            total_cust = await db.scalar(total_query) or 1

            conversion_rate = signed / total_cust if total_cust > 0 else 0

            # Get follow up count
            follow_query = select(func.count(FollowUp.id)).where(
                and_(
                    FollowUp.sale_id == row.sale_id,
                    FollowUp.created_at >= period_range.start
                )
            )
            follow_count = await db.scalar(follow_query) or 0

            ranking.append(type('RankingItem', (), {
                'rank': rank,
                'sale_id': row.sale_id,
                'sale_name': row.sale_name,
                'team': row.team,
                'order_count': order_count,
                'revenue': total_rev,
                'avg_order_value': avg_order,
                'conversion_rate': conversion_rate,
                'follow_up_count': follow_count
            })())
            rank += 1

        return ranking, total
