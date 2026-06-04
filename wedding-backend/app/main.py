from __future__ import annotations
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import traceback

from app.config import settings
from app.database import get_db
from app.utils.errors import AppException, ErrorDetail
from app.api import auth, customers, suppliers, orders, approvals, events, venues, dashboard, users, notifications, reports, imports, health
from app.dashboard.interfaces.controllers import (
    health_controller,
    cashflow_controller,
    team_efficiency_controller,
    alerts_controller,
    decision_support_controller,
)
from app.events.handlers import register_event_handlers
from app.finance.interfaces.controllers import receivables, payments, refunds, transactions, invoices, reconciliations
from app.finance.interfaces.subscribers.event_handlers import register_finance_event_handlers
from app.middleware.logging import setup_structured_logging, StructuredLoggingMiddleware
from app.middleware.request_id import RequestIDMiddleware
from app.middleware.rate_limit import limiter, rate_limit_exceeded_handler
from app.middleware.global_rate_limit import GlobalRateLimitMiddleware
from app.middleware.metrics import MetricsMiddleware, get_metrics
from app.middleware.csrf import CSRFMiddleware
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
cors_origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global rate limiting middleware
app.add_middleware(GlobalRateLimitMiddleware)

# Metrics middleware
app.add_middleware(MetricsMiddleware)

# CSRF protection middleware
app.add_middleware(CSRFMiddleware)


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
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(customers.router, prefix="/api/v1", tags=["customers"])
app.include_router(suppliers.router, prefix="/api/v1/suppliers", tags=["suppliers"])
app.include_router(orders.router, prefix="/api/v1/orders", tags=["orders"])
app.include_router(approvals.router, prefix="/api/v1/approvals", tags=["approvals"])
app.include_router(events.router, prefix="/api/v1/events", tags=["events"])
app.include_router(venues.router, prefix="/api/v1/venues", tags=["venues"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["dashboard"])
# New Dashboard v2 APIs
app.include_router(health_controller.router, prefix="/api/v1/dashboard", tags=["dashboard-v2"])
app.include_router(cashflow_controller.router, prefix="/api/v1/dashboard", tags=["dashboard-v2"])
app.include_router(team_efficiency_controller.router, prefix="/api/v1/dashboard", tags=["dashboard-v2"])
app.include_router(alerts_controller.router, prefix="/api/v1/dashboard", tags=["dashboard-v2"])
app.include_router(decision_support_controller.router, prefix="/api/v1/dashboard", tags=["dashboard-v2"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(notifications.router, prefix="/api/v1/notifications", tags=["notifications"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["reports"])
app.include_router(imports.router, prefix="/api/v1/imports", tags=["imports"])

# Finance module routes
app.include_router(receivables.router, prefix="/api/v1/finance/receivables", tags=["finance-receivables"])
app.include_router(payments.router, prefix="/api/v1/finance/payments", tags=["finance-payments"])
app.include_router(refunds.router, prefix="/api/v1/finance/refunds", tags=["finance-refunds"])
app.include_router(transactions.router, prefix="/api/v1/finance/transactions", tags=["finance-transactions"])
app.include_router(invoices.router, prefix="/api/v1/finance/invoices", tags=["finance-invoices"])
app.include_router(reconciliations.router, prefix="/api/v1/finance/reconciliations", tags=["finance-reconciliations"])


# Metrics endpoint for Prometheus
@app.get("/metrics", tags=["metrics"])
async def metrics():
    return get_metrics()


@app.on_event("startup")
async def startup():
    register_event_handlers()
    register_finance_event_handlers()
    logger.info("Application startup complete", extra={"event": "startup"})

    # Initialize Sentry if DSN is provided
    sentry_dsn = getattr(settings, "SENTRY_DSN", None)
    if sentry_dsn:
        from app.sentry import init_sentry
        init_sentry(sentry_dsn)


@app.on_event("shutdown")
async def shutdown():
    logger.info("Application shutdown initiated", extra={"event": "shutdown"})
    # Close database connections
    from app.database import engine
    await engine.dispose()
    logger.info("Application shutdown complete", extra={"event": "shutdown"})