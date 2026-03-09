"""
Flux Backend — Onboarding Service

DB operations for onboarding: update users.profile, set onboarded=true,
and fetch user with onboarding status for GET /account/me.
"""

from __future__ import annotations

from app.database import get_supabase_client


def _db():
    return get_supabase_client()


async def save_profile(user_id: str, profile_data: dict) -> None:
    """
    Update users.profile JSONB and set onboarded=true.
    Must be awaited before returning the final chat response so the frontend
    sees onboarded=true on the next refreshAuthStatus().
    """
    _db().table("users").update(
        {
            "profile": profile_data,
            "onboarded": True,
        }
    ).eq("id", user_id).execute()


async def is_user_onboarded(user_id: str) -> bool:
    """Return whether the user has completed onboarding."""
    result = _db().table("users").select("onboarded").eq("id", user_id).execute()
    rows = result.data if result.data else []
    if not rows:
        return False
    return bool(rows[0].get("onboarded", False))


async def get_user_with_onboarding_status(user_id: str) -> dict | None:
    """
    Return user row including onboarded and profile.
    Used by GET /account/me or equivalent.
    """
    result = _db().table("users").select("*").eq("id", user_id).execute()
    rows = result.data if result.data else []
    return rows[0] if rows else None
