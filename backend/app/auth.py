"""
Flux Backend — JWT Authentication

FastAPI dependency for JWT validation via Supabase JWKS.

Usage in route handlers:
    from app.auth import get_current_user

    @router.get("/protected")
    async def protected_route(user: dict = Depends(get_current_user)):
        user_id = user["sub"]
        ...

Pattern reference: flux-backend/app/middleware/auth.py
"""

from __future__ import annotations

import logging

import jwt
from jwt import PyJWKClient
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings

logger = logging.getLogger(__name__)

# Supabase exposes signing keys via a standard JWKS endpoint.
# PyJWKClient caches keys in memory; actual fetch is lazy (first request).
_JWKS_URL = f"{settings.supabase_url}/auth/v1/.well-known/jwks.json"
_jwks_client = PyJWKClient(_JWKS_URL, cache_keys=True)

_bearer = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> dict:
    """
    Validate a Supabase JWT and return the decoded payload.

    The user UUID is available as ``payload["sub"]``.
    Raises HTTP 401 if the token is invalid, expired, or missing.
    """
    token = credentials.credentials
    try:
        signing_key = _jwks_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256"],
            audience="authenticated",
        )
    except jwt.ExpiredSignatureError:
        logger.warning("JWT validation failed: token expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as exc:
        logger.warning("JWT validation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return payload
