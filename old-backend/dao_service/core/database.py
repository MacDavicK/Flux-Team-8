"""
Framework-agnostic database session management.

Defines the DatabaseSession protocol and provides the SQLAlchemy implementation.
Engine creation is lazy to allow tests to run without asyncpg installed.
"""

from typing import AsyncGenerator, Optional, Protocol

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession as SQLAlchemyAsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from dao_service.config import settings


class DatabaseSession(Protocol):
    """
    Framework-agnostic database session protocol.

    Any ORM framework's session type can satisfy this protocol.
    The protocol is intentionally thin — only transaction lifecycle methods.
    Query execution is framework-specific and handled inside DAO implementations.
    """

    async def __aenter__(self): ...
    async def __aexit__(self, exc_type, exc_val, exc_tb): ...
    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...
    async def close(self) -> None: ...


# Lazy engine/session initialization — avoids importing asyncpg at module level
_engine: Optional[AsyncEngine] = None
_session_factory: Optional[async_sessionmaker] = None


def _get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            settings.DATABASE_URL,
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            pool_pre_ping=True,
            pool_recycle=settings.DB_POOL_RECYCLE,
        )
    return _engine


def _get_session_factory() -> async_sessionmaker:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            _get_engine(),
            class_=SQLAlchemyAsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


def AsyncSessionLocal() -> SQLAlchemyAsyncSession:
    """Create a new async session. Used by get_db and the /ready endpoint."""
    return _get_session_factory()()


async def get_db() -> AsyncGenerator[DatabaseSession, None]:
    """Yields a SQLAlchemy session typed as generic DatabaseSession."""
    session = AsyncSessionLocal()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
