from __future__ import annotations
from fastapi import APIRouter, status
from pydantic import BaseModel
from sqlalchemy import text
from app.database import get_db
from app.utils.cache import redis_client

router = APIRouter(tags=["health"])


class LivenessResponse(BaseModel):
    status: str = "ok"


class ReadinessStatus(BaseModel):
    mysql: str
    redis: str


class ReadinessResponse(BaseModel):
    status: str
    services: ReadinessStatus


@router.get("/health", response_model=LivenessResponse)
async def liveness():
    """Liveness probe - application is running."""
    return LivenessResponse(status="ok")


@router.get("/ready", response_model=ReadinessResponse)
async def readiness(db=get_db):
    """Readiness probe - application can serve traffic."""
    mysql_status = "ok"
    redis_status = "ok"

    try:
        async with db as session:
            await session.execute(text("SELECT 1"))
    except Exception:
        mysql_status = "error"

    try:
        await redis_client.ping()
    except Exception:
        redis_status = "error"

    overall = "ok" if mysql_status == "ok" and redis_status == "ok" else "degraded"

    return ReadinessResponse(
        status=overall,
        services=ReadinessStatus(mysql=mysql_status, redis=redis_status)
    )