"""
16.1 — Auth Middleware (app/middleware/auth.py) — §11, §13

FastAPI dependency for JWT authentication via Supabase.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.services.supabase import supabase

_bearer = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
):
    """
    16.1.1 — HTTPBearer dependency.
    16.1.2 — Validates JWT via supabase.auth.get_user(); raises HTTP 401 on failure.
    16.1.3 — Returns user object with user.id accessible downstream.
    """
    token = credentials.credentials
    try:
        response = supabase.auth.get_user(token)
        user = response.user
        if user is None:
            raise ValueError("No user in response")
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
