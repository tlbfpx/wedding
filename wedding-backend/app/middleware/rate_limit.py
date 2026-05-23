from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi.responses import JSONResponse


limiter = Limiter(key_func=get_remote_address)


async def rate_limit_exceeded_handler(request, exc):
    return JSONResponse(
        status_code=429,
        content={"error": {"code": "RATE_LIMIT_EXCEEDED", "message": "Too many requests. Please try again later.", "detail": None}},
        headers={"Retry-After": str(exc.detail)}
    )