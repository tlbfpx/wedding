"""Legacy controller with deprecation headers."""
from __future__ import annotations
from fastapi import APIRouter, Response
from fastapi import Depends

# Import the old dashboard router functions to wrap them
from app.api.dashboard import (
    get_overview,
    get_sales_ranking,
    get_conversion_funnel,
    get_finance_summary,
)

router = APIRouter()


@router.get("/overview", deprecated=True)
async def overview_with_deprecation(*args, **kwargs):
    """Deprecated: Use GET /api/v1/dashboard/health instead."""
    result = await get_overview(*args, **kwargs)
    return result


@router.get("/sales-ranking", deprecated=True)
async def sales_ranking_with_deprecation(*args, **kwargs):
    """Deprecated: Use GET /api/v1/dashboard/team-efficiency instead."""
    result = await get_sales_ranking(*args, **kwargs)
    return result


@router.get("/conversion-funnel", deprecated=True)
async def conversion_funnel_with_deprecation(*args, **kwargs):
    """Deprecated: Use GET /api/v1/dashboard/team-efficiency instead."""
    result = await get_conversion_funnel(*args, **kwargs)
    return result


@router.get("/finance-summary", deprecated=True)
async def finance_summary_with_deprecation(*args, **kwargs):
    """Deprecated: Use GET /api/v1/dashboard/cashflow instead."""
    result = await get_finance_summary(*args, **kwargs)
    return result
