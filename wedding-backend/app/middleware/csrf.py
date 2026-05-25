from __future__ import annotations
"""
CSRF protection middleware.
Validates X-CSRF-Token header on state-changing operations.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class CSRFMiddleware(BaseHTTPMiddleware):
    """
    CSRF protection that:
    - Allows GET, HEAD, OPTIONS requests through without validation
    - Requires X-CSRF-Token header for POST, PUT, PATCH, DELETE requests
    - Exempts /api/v1/auth/login (open login endpoint)
    """

    EXEMPT_PATHS = {
        "/api/v1/auth/login",
        "/api/v1/auth/refresh",
        "/api/v1/auth/csrf",
        "/api/v1/auth/logout",  # requires auth, so safe - but would need CSRF token in real deployment
        "/metrics",
        "/api/v1/health",
        "/api/v1/ready",
    }

    SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}

    async def dispatch(self, request: Request, call_next):
        # Skip safe methods
        if request.method in self.SAFE_METHODS:
            return await call_next(request)

        # Check exemption
        path = request.url.path
        if any(path.startswith(p) for p in self.EXEMPT_PATHS):
            return await call_next(request)

        # Validate CSRF token
        csrf_token = request.headers.get("X-CSRF-Token")
        if not csrf_token:
            return JSONResponse(
                status_code=403,
                content={"detail": {"code": "CSRF_MISSING", "message": "CSRF token required"}},
            )

        # Token validation (simple presence check - backend sets it as a secrets token)
        # In production, this could be tied to the session
        if len(csrf_token) < 16:
            return JSONResponse(
                status_code=403,
                content={"detail": {"code": "CSRF_INVALID", "message": "Invalid CSRF token"}},
            )

        return await call_next(request)