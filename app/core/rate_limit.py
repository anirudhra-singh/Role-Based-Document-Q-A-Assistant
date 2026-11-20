from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.core.config import get_settings

LOGIN_LIMIT = "5/minute"
REFRESH_LIMIT = "10/minute"


limiter = Limiter(key_func=get_remote_address, enabled=get_settings().rate_limit_enabled)


def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests. Try again later."},
        headers={"Retry-After": "60"},
    )