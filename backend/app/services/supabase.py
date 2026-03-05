import asyncpg
from supabase import create_client, Client

from app.config import settings

# ─────────────────────────────────────────────────────────────────
# asyncpg connection pool
# ─────────────────────────────────────────────────────────────────

_pool: asyncpg.Pool | None = None


async def init_pool() -> None:
    global _pool
    # Strip the +asyncpg dialect prefix — asyncpg expects a plain postgres:// DSN
    dsn = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    _pool = await asyncpg.create_pool(dsn=dsn, min_size=2, max_size=10)


async def close_pool() -> None:
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


def get_pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("Database pool is not initialized. Call init_pool() first.")
    return _pool


# ─────────────────────────────────────────────────────────────────
# Query helpers
# ─────────────────────────────────────────────────────────────────

class _Database:
    async def fetch(self, query: str, *args) -> list[asyncpg.Record]:
        async with get_pool().acquire() as conn:
            return await conn.fetch(query, *args)

    async def fetchrow(self, query: str, *args) -> asyncpg.Record | None:
        async with get_pool().acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def execute(self, query: str, *args) -> str:
        async with get_pool().acquire() as conn:
            return await conn.execute(query, *args)

    async def fetchval(self, query: str, *args):
        async with get_pool().acquire() as conn:
            return await conn.fetchval(query, *args)


db = _Database()

# ─────────────────────────────────────────────────────────────────
# Supabase client (anon key — used for JWT validation only)
# ─────────────────────────────────────────────────────────────────

supabase: Client = create_client(settings.supabase_url, settings.supabase_anon_key)
