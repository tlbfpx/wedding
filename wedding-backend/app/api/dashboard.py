from datetime import date, datetime, timedelta
from typing import Optional
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, and_, case, extract
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Customer, Order, Payment, Supplier, SupplierEvaluation, Event
from app.models.customer import CustomerStatus
from app.models.order import OrderStatus
from app.models.supplier import SupplierType
from app.models.user import User, TeamEnum
from app.models.event import EventStatus
from app.middleware.auth import get_current_user
from app.utils.cache import redis_client
import json

router = APIRouter()


def _period_to_dates(period: str) -> tuple[datetime, datetime]:
    now = datetime.utcnow()
    if period == "month":
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif period == "quarter":
        quarter_month = ((now.month - 1) // 3) * 3 + 1
        start = now.replace(month=quarter_month, day=1, hour=0, minute=0, second=0, microsecond=0)
    elif period == "year":
        start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return start, now


# ── Routes ───────────────────────────────────────────────────────────────────

@router.get("/overview")
async def get_overview(
    period: str = Query("month", regex="^(month|quarter|year)$"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    cache_key = f"dashboard:overview:{period}"
    cached = await redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    start, now = _period_to_dates(period)

    # Customer counts by status
    customer_counts = await db.execute(
        select(
            Customer.status,
            func.count(Customer.id),
        )
        .where(Customer.created_at >= start)
        .group_by(Customer.status)
    )
    status_counts = {row[0].value: row[1] for row in customer_counts.all()}

    # Total customers
    total_customers = await db.execute(select(func.count(Customer.id)))
    total_c = total_customers.scalar_one()

    # Order stats
    order_stats = await db.execute(
        select(
            func.count(Order.id),
            func.sum(Order.total_amount),
            func.sum(Order.paid_amount),
        )
        .where(Order.created_at >= start)
    )
    order_count, total_amount, paid_amount = order_stats.one()

    # Upcoming events
    event_count = await db.execute(
        select(func.count(Event.id)).where(
            Event.date >= now.date(),
            Event.status != "cancelled",
        )
    )

    data = {
        "period": period,
        "customers": {
            "total": total_c,
            "by_status": status_counts,
        },
        "orders": {
            "count": order_count or 0,
            "total_amount": float(total_amount or 0),
            "paid_amount": float(paid_amount or 0),
        },
        "upcoming_events": event_count.scalar_one(),
    }

    await redis_client.setex(cache_key, 300, json.dumps(data, default=str))
    return data


@router.get("/sales-ranking")
async def get_sales_ranking(
    period: str = Query("month", regex="^(month|quarter|year)$"),
    team: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    start, now = _period_to_dates(period)

    query = (
        select(
            User.id,
            User.name,
            func.count(Order.id).label("order_count"),
            func.sum(Order.total_amount).label("total_amount"),
        )
        .join(Order, Order.sale_id == User.id)
        .where(
            Order.created_at >= start,
            Order.status != OrderStatus.cancelled,
        )
        .group_by(User.id, User.name)
        .order_by(func.sum(Order.total_amount).desc())
    )

    if team:
        query = query.where(User.team == team)

    result = await db.execute(query)
    rows = result.all()

    return {
        "period": period,
        "ranking": [
            {
                "sale_id": row.id,
                "sale_name": row.name,
                "order_count": row.order_count,
                "total_amount": float(row.total_amount or 0),
            }
            for row in rows
        ],
    }


@router.get("/conversion-funnel")
async def get_conversion_funnel(
    date_start: Optional[date] = Query(None),
    date_end: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = select(
        Customer.status,
        func.count(Customer.id),
    ).group_by(Customer.status)

    if date_start:
        query = query.where(Customer.created_at >= datetime.combine(date_start, datetime.min.time()))
    if date_end:
        query = query.where(Customer.created_at <= datetime.combine(date_end, datetime.max.time()))

    result = await db.execute(query)
    status_counts = {row[0].value: row[1] for row in result.all()}

    funnel_order = ["potential", "following", "intention", "signed", "lost"]
    funnel = []
    for status in funnel_order:
        count = status_counts.get(status, 0)
        funnel.append({"status": status, "count": count})

    return {"funnel": funnel}


@router.get("/finance-summary")
async def get_finance_summary(
    period: str = Query("month", regex="^(month|quarter|year)$"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    start, now = _period_to_dates(period)

    # Total order amount
    order_result = await db.execute(
        select(
            func.count(Order.id),
            func.sum(Order.total_amount),
        )
        .where(
            Order.created_at >= start,
            Order.status != OrderStatus.cancelled,
        )
    )
    order_count, total_amount = order_result.one()

    # Total paid
    paid_result = await db.execute(
        select(func.sum(Payment.amount))
        .where(
            Payment.created_at >= start,
            Payment.status == "confirmed",
        )
    )
    total_paid = paid_result.scalar_one() or 0

    # Receivable
    receivable = Decimal(str(total_amount or 0)) - Decimal(str(total_paid))

    # Payment method breakdown
    method_result = await db.execute(
        select(Payment.method, func.sum(Payment.amount))
        .where(
            Payment.created_at >= start,
            Payment.status == "confirmed",
        )
        .group_by(Payment.method)
    )
    method_breakdown = {row[0].value: float(row[1] or 0) for row in method_result.all()}

    return {
        "period": period,
        "order_count": order_count or 0,
        "total_amount": float(total_amount or 0),
        "total_paid": float(total_paid),
        "receivable": float(receivable),
        "payment_method_breakdown": method_breakdown,
    }


@router.get("/schedule-heatmap")
async def get_schedule_heatmap(
    month: str = Query(..., description="YYYY-MM format"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    year, m = month.split("-")
    year, m = int(year), int(m)

    result = await db.execute(
        select(
            Event.date,
            func.count(Event.id),
        )
        .where(
            extract("year", Event.date) == year,
            extract("month", Event.date) == m,
            Event.status != EventStatus.cancelled,
        )
        .group_by(Event.date)
        .order_by(Event.date)
    )
    rows = result.all()

    heatmap = [{"date": str(row[0]), "count": row[1]} for row in rows]

    return {"month": month, "heatmap": heatmap}


@router.get("/supplier-ranking")
async def get_supplier_ranking(
    type: Optional[SupplierType] = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = (
        select(
            Supplier.id,
            Supplier.name,
            Supplier.type,
            Supplier.rating,
            func.count(SupplierEvaluation.id).label("evaluation_count"),
        )
        .outerjoin(SupplierEvaluation, SupplierEvaluation.supplier_id == Supplier.id)
        .group_by(Supplier.id, Supplier.name, Supplier.type, Supplier.rating)
        .order_by(Supplier.rating.desc())
    )

    if type:
        query = query.where(Supplier.type == type)

    result = await db.execute(query)
    rows = result.all()

    return {
        "ranking": [
            {
                "supplier_id": row.id,
                "supplier_name": row.name,
                "type": row.type.value,
                "rating": float(row.rating),
                "evaluation_count": row.evaluation_count,
            }
            for row in rows
        ],
    }
