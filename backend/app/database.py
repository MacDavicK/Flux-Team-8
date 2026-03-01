"""
Flux Backend — Supabase Client

Initializes and exposes the Supabase client for database operations.
Uses lazy initialization so tests can mock before the client is created.

- get_supabase_client(): uses SUPABASE_KEY (anon/publishable). Use for
  operations that run as the current user or for auth.
- get_supabase_admin_client(): uses SUPABASE_SERVICE_ROLE_KEY when set;
  bypasses RLS. Use for server-side writes (e.g. syncing auth user to public.users).
  Falls back to SUPABASE_KEY if service role key is not set.
"""

from typing import Optional
from supabase import create_client, Client
from app.config import settings

_client: Optional[Client] = None
_admin_client: Optional[Client] = None


def get_supabase_client() -> Client:
    """Get or create the Supabase client (lazy singleton). Uses SUPABASE_KEY."""
    global _client
    if _client is None:
        _client = create_client(settings.supabase_url, settings.supabase_key)
    return _client


def get_supabase_admin_client() -> Client:
    """
    Get or create a Supabase client that bypasses RLS (for server-side writes).
    Uses SUPABASE_SERVICE_ROLE_KEY when set, otherwise SUPABASE_KEY.
    """
    global _admin_client
    if _admin_client is None:
        key = (
            settings.supabase_service_role_key
            if getattr(settings, "supabase_service_role_key", "")
            else settings.supabase_key
        )
        _admin_client = create_client(settings.supabase_url, key)
    return _admin_client
