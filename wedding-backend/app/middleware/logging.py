from __future__ import annotations
import logging
import time
import json
from typing import Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware that logs requests in structured JSON format."""

    def __init__(self, app, logger_name: str = "app.access"):
        super().__init__(app)
        self.logger = logging.getLogger(logger_name)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.perf_counter()

        # Extract user_id if available from request state
        user_id = getattr(request.state, "user_id", None)

        response = await call_next(request)

        duration_ms = (time.perf_counter() - start_time) * 1000

        log_data = {
            "event": "http_request",
            "method": request.method,
            "path": str(request.url.path),
            "status_code": response.status_code,
            "duration_ms": round(duration_ms, 2),
            "client_ip": request.client.host if request.client else None,
        }

        # Add request_id if available
        request_id = getattr(request.state, "request_id", None)
        if request_id:
            log_data["request_id"] = request_id

        # Add user_id if available
        if user_id:
            log_data["user_id"] = user_id

        # Add query params if present (sanitized)
        if request.query_params:
            log_data["query_params"] = dict(request.query_params)

        # Log based on status code
        if response.status_code >= 500:
            self.logger.error(json.dumps(log_data))
        elif response.status_code >= 400:
            self.logger.warning(json.dumps(log_data))
        else:
            self.logger.info(json.dumps(log_data))

        return response


def setup_structured_logging():
    """Configure structured JSON logging for the application."""
    # Create formatters
    class StructuredFormatter(logging.Formatter):
        def format(self, record):
            log_data = {
                "time": self.formatTime(record, self.datefmt),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
            }

            # Add request_id if available in record
            if hasattr(record, "request_id"):
                log_data["request_id"] = record.request_id

            # Add extra fields
            if hasattr(record, "extra_data"):
                log_data.update(record.extra_data)

            return json.dumps(log_data)

    # Configure root logger
    root_logger = logging.getLogger("app")
    root_logger.setLevel(logging.INFO)

    # Remove existing handlers
    root_logger.handlers.clear()

    # Add structured handler
    handler = logging.StreamHandler()
    handler.setFormatter(StructuredFormatter())
    root_logger.addHandler(handler)

    # Configure access logger
    access_logger = logging.getLogger("app.access")
    access_logger.setLevel(logging.INFO)
    access_logger.handlers.clear()

    access_handler = logging.StreamHandler()
    access_handler.setFormatter(StructuredFormatter())
    access_logger.addHandler(access_handler)


def get_request_logger(name: str = "app") -> logging.Logger:
    """Get a logger that includes request context."""
    return logging.getLogger(name)


# ── log_operation helper ──────────────────────────────────────────────────────

async def log_operation(db, user_id: int, request, detail: dict):
    """Log a user operation to the database operation_logs table."""
    from app.models.log import OperationLog
    from starlette.requests import Request as StarletteRequest

    # Extract operation info
    module = _extract_module(request.url.path if hasattr(request, "url") else str(request))
    action = _extract_action(request.method if hasattr(request, "method") else "unknown")
    target = str(detail)[:100]
    ip = request.client.host if hasattr(request, "client") and request.client else None

    op_log = OperationLog(
        user_id=user_id,
        module=module,
        action=action,
        target=target,
        detail=str(detail),
        ip=ip,
    )
    db.add(op_log)
    await db.commit()


def _extract_module(path: str) -> str:
    """Extract module name from API path."""
    parts = path.strip("/").split("/")
    # /api/v1/customers -> customers, /api/v1/suppliers -> suppliers, etc.
    if len(parts) >= 3:
        return parts[2]  # customers, suppliers, orders, etc.
    if len(parts) >= 2:
        return parts[1]
    return "unknown"


def _extract_action(method: str) -> str:
    """Map HTTP method to action name."""
    mapping = {"GET": "read", "POST": "create", "PUT": "update", "PATCH": "update", "DELETE": "delete"}
    return mapping.get(method.upper(), method.lower())