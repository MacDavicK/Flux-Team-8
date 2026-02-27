"""Pattern DTOs."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import Field

from dao_service.schemas.base import BaseSchema


class PatternBase(BaseSchema):
    pattern_type: Optional[str] = None
    description: Optional[str] = None
    data: Optional[dict] = None
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class PatternCreateDTO(PatternBase):
    user_id: UUID


class PatternUpdateDTO(BaseSchema):
    pattern_type: Optional[str] = None
    description: Optional[str] = None
    data: Optional[dict] = None
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class PatternDTO(PatternBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime
