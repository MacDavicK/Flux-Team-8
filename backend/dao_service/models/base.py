"""Declarative base and ORM mixins."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import TIMESTAMP, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all models."""

    pass


class UUIDMixin:
    """Provides a UUID primary key that defaults to gen_random_uuid() on the server."""

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )


class TimestampMixin:
    """Provides a created_at timestamp that defaults to now()."""

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )
