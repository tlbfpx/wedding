from __future__ import annotations
import time
from collections import defaultdict
from threading import Lock
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class InMemoryRateLimiter:
    """Simple in-memory rate limiter for global protection."""

    def __init__(self, max_requests: int = 10000, window: int = 60):
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()
        self._window = window  # 1 minute window
        self._max_requests = max_requests

    def is_allowed(self, key: str) -> bool:
        now = time.time()
        with self._lock:
            # Clean old entries
            self._requests[key] = [
                t for t in self._requests[key] if now - t < self._window
            ]
            if len(self._requests[key]) >= self._max_requests:
                return False
            self._requests[key].append(now)
            return True

    def reset(self):
        """Reset all rate limit data. Used for testing."""
        with self._lock:
            self._requests.clear()


_global_limiter = InMemoryRateLimiter()


class GlobalRateLimitMiddleware(BaseHTTPMiddleware):
    """Global rate limiting middleware."""

    EXCLUDED_PATHS = {"/api/v1/health", "/api/v1/ready", "/api/docs", "/api/redoc", "/metrics"}

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health/readiness docs endpoints
        path = request.url.path
        if any(path.startswith(p) for p in self.EXCLUDED_PATHS):
            return await call_next(request)

        # Get client IP (considering proxies)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"

        if not _global_limiter.is_allowed(client_ip):
            return JSONResponse(
                status_code=429,
                content={"error": {"code": "RATE_LIMIT_EXCEEDED", "message": "请求过于频繁，请稍后再试。", "detail": None}},
                headers={"Retry-After": "60"}
            )

        return await call_next(request)