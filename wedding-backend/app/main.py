from __future__ import annotations
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import traceback

from app.config import settings
from app.database import get_db
from app.utils.errors import AppException, ErrorDetail
from app.api import auth, customers, suppliers, orders, approvals, events, venues, dashboard, users, notifications, reports, imports
from app.events.handlers import register_event_handlers
from app.middleware.logging import setup_structured_logging, StructuredLoggingMiddleware
from app.middleware.request_id import RequestIDMiddleware
from app.middleware.rate_limit import limiter, rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

# Setup structured logging first
setup_structured_logging()
logger = logging.getLogger("app")

app = FastAPI(title=settings.APP_NAME, docs_url="/api/docs", redoc_url="/api/redoc")

# Add rate limiter
app.state.limiter = limiter

# Add request ID middleware first
app.add_middleware(RequestIDMiddleware)

# Add structured logging middleware
app.add_middleware(StructuredLoggingMiddleware)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    request_id = getattr(request.state, "request_id", "unknown")
    logger.warning(
        f"AppException occurred: {exc.error.message}",
        extra={"request_id": request_id, "extra_data": {"status_code": exc.status_code, "error_code": exc.error.code}}
    )
    return JSONResponse(status_code=exc.status_code, content={"error": exc.error.model_dump()})


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return await rate_limit_exceeded_handler(request, exc)


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Handle unhandled exceptions - log full traceback but return clean response."""
    request_id = getattr(request.state, "request_id", "unknown")
    tb_str = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))

    logger.error(
        f"Unhandled exception: {str(exc)}",
        extra={"request_id": request_id, "extra_data": {"exception_type": type(exc).__name__, "traceback": tb_str}}
    )

    # Return clean error response without exposing stack trace
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An internal error occurred. Please try again later.",
                "detail": None
            }
        }
    )


app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(customers.router, prefix="/api/v1", tags=["customers"])
app.include_router(suppliers.router, prefix="/api/v1/suppliers", tags=["suppliers"])
app.include_router(orders.router, prefix="/api/v1/orders", tags=["orders"])
app.include_router(approvals.router, prefix="/api/v1/approvals", tags=["approvals"])
app.include_router(events.router, prefix="/api/v1/events", tags=["events"])
app.include_router(venues.router, prefix="/api/v1/venues", tags=["venues"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["dashboard"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(notifications.router, prefix="/api/v1/notifications", tags=["notifications"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["reports"])
app.include_router(imports.router, prefix="/api/v1/imports", tags=["imports"])


@app.on_event("startup")
async def startup():
    register_event_handlers()
    logger.info("Application startup complete", extra={"event": "startup"})

    # Initialize Sentry if DSN is provided
    sentry_dsn = getattr(settings, "SENTRY_DSN", None)
    if sentry_dsn:
        from app.sentry import init_sentry
        init_sentry(sentry_dsn)