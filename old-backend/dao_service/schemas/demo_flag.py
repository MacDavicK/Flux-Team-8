"""DemoFlag DTOs."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import Field

from dao_service.schemas.base import BaseSchema


class DemoFlagBase(BaseSchema):
    virtual_now: Optional[datetime] = None
    escalation_speed: float = Field(default=1.0, ge=0.0)


class DemoFlagCreateDTO(DemoFlagBase):
    user_id: UUID


class DemoFlagDTO(DemoFlagBase):
    user_id: UUID
