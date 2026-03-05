"""
16.3 — Rate Limiting (app/middleware/rate_limit.py) — §16

slowapi Limiter using per-user key function and Redis storage.
"""
from fastapi import Request
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded  # re-exported for convenience
from slowapi.util import get_remote_address

from app.config import settings


def _user_key(request: Request) -> str:
    """
    16.3.1 — Per-user key: use user.id from request.state if available,
    otherwise fall back to IP address (for un-authenticated endpoints).
    """
    user = getattr(request.state, "user", None)
    if user is not None:
        return str(getattr(user, "id", None) or get_remote_address(request))
    return get_remote_address(request)


# 16.3.1 — Limiter with Redis storage; disabled in non-production environments
limiter = Limiter(
    key_func=_user_key,
    storage_uri=settings.redis_url,
    enabled=settings.app_env == "production",
)

__all__ = ["limiter", "RateLimitExceeded"]
