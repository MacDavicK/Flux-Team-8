import asyncio

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
    _pool = await asyncpg.create_pool(
        dsn=dsn,
        min_size=2,
        max_size=10,
        # Evict idle connections after 55s — just under Supabase's 60s server-side
        # idle timeout so the pool never hands out a connection the server already
        # closed silently.
        max_inactive_connection_lifetime=55,
    )


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

_RETRY_EXCEPTIONS = (
    asyncpg.exceptions.ConnectionDoesNotExistError,
    asyncpg.exceptions.ConnectionFailureError,
)
_MAX_RETRIES = 2


class _Database:
    async def _run(self, fn, query: str, *args):
        """Acquire a connection and execute fn, retrying on dropped connections."""
        for attempt in range(_MAX_RETRIES + 1):
            try:
                async with get_pool().acquire() as conn:
                    return await fn(conn, query, *args)
            except _RETRY_EXCEPTIONS:
                if attempt == _MAX_RETRIES:
                    raise
                await asyncio.sleep(0.1 * (2**attempt))

    async def fetch(self, query: str, *args) -> list[asyncpg.Record]:
        return await self._run(lambda c, q, *a: c.fetch(q, *a), query, *args)

    async def fetchrow(self, query: str, *args) -> asyncpg.Record | None:
        return await self._run(lambda c, q, *a: c.fetchrow(q, *a), query, *args)

    async def execute(self, query: str, *args) -> str:
        return await self._run(lambda c, q, *a: c.execute(q, *a), query, *args)

    async def fetchval(self, query: str, *args):
        return await self._run(lambda c, q, *a: c.fetchval(q, *a), query, *args)

    async def executemany(self, query: str, args_list: list) -> None:
        async def _fn(conn, q, *_):
            return await conn.executemany(q, args_list)

        await self._run(_fn, query)


db = _Database()

# ─────────────────────────────────────────────────────────────────
# Supabase client (anon key — used for JWT validation only)
# ─────────────────────────────────────────────────────────────────

supabase: Client = create_client(settings.supabase_url, settings.supabase_anon_key)
