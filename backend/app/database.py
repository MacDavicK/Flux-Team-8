"""
Flux Backend — Supabase Client

Initializes and exposes the Supabase client for database operations.
Uses lazy initialization so tests can mock before the client is created.
"""

from typing import Optional
from supabase import create_client, Client
from app.config import settings

_client: Optional[Client] = None


def get_supabase_client() -> Client:
    """Get or create the Supabase client (lazy singleton)."""
    global _client
    if _client is None:
        _client = create_client(settings.supabase_url, settings.supabase_key)
    return _client
