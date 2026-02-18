"""Base schema classes and mixins for all DTOs."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    """Base for all DTOs with ORM mode enabled."""

    model_config = ConfigDict(from_attributes=True)


class IDMixin(BaseModel):
    """Provides UUID id field."""

    id: UUID


class TimestampMixin(BaseModel):
    """Provides created_at field."""

    created_at: datetime
