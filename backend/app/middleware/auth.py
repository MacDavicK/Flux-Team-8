"""
16.1 — Auth Middleware (app/middleware/auth.py) — §11, §13

FastAPI dependency for JWT authentication via Supabase.
"""
import logging
import os
import uuid

import jwt
from jwt import PyJWKClient
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger(__name__)

_SUPABASE_URL = os.getenv("SUPABASE_URL")
_JWKS_URL = f"{_SUPABASE_URL}/auth/v1/.well-known/jwks.json"
_jwks_client = PyJWKClient(_JWKS_URL, cache_keys=True)

_bearer = HTTPBearer()


async def _upsert_user(payload: dict) -> None:
    """Ensure a users row exists for this Supabase auth identity.

    Called after every successful JWT validation so new sign-ups automatically
    get a Postgres row without needing a separate registration endpoint.
    On insert, seeds profile.name from Google OAuth user_metadata if present.
    Uses INSERT … ON CONFLICT DO NOTHING to avoid clobbering existing data.
    """
    import json
    from app.services.supabase import db  # local import to avoid circular dep

    user_metadata = payload.get("user_metadata") or {}
    full_name = user_metadata.get("full_name") or user_metadata.get("name")

    try:
        if full_name:
            # Insert or, if the row already exists with no name in profile, backfill it.
            await db.execute(
                """
                INSERT INTO users (id, email, profile)
                VALUES ($1, $2, $3::jsonb)
                ON CONFLICT (id) DO UPDATE
                  SET profile = CASE
                    WHEN users.profile IS NULL OR (users.profile->>'name') IS NULL
                    THEN COALESCE(users.profile, '{}'::jsonb) || $3::jsonb
                    ELSE users.profile
                  END
                """,
                uuid.UUID(str(payload["sub"])),
                payload.get("email"),
                json.dumps({"name": full_name}),
            )
        else:
            await db.execute(
                """
                INSERT INTO users (id, email)
                VALUES ($1, $2)
                ON CONFLICT (id) DO NOTHING
                """,
                uuid.UUID(str(payload["sub"])),
                payload.get("email"),
            )
    except Exception as exc:
        # Non-fatal: log and continue. The request will still succeed and the
        # next call will retry the upsert.
        logger.warning("Failed to upsert user row: %s", exc)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
):
    """
    16.1.1 — HTTPBearer dependency.
    16.1.2 — Validates JWT locally via JWKS; raises HTTP 401 on failure.
    16.1.3 — Returns decoded JWT payload dict; user ID accessible via payload["sub"].
    16.1.4 — Upserts a users row on every authenticated request so new sign-ups
              are provisioned automatically without a separate registration call.
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

    await _upsert_user(payload)
    return payload
