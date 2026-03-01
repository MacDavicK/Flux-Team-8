"""User DTOs."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import Field

from dao_service.schemas.base import BaseSchema


class UserBase(BaseSchema):
    email: str = Field(..., min_length=1, max_length=255)


class UserCreateDTO(UserBase):
    onboarded: bool = False
    profile: Optional[dict] = None
    notification_preferences: Optional[dict] = None


class UserUpdateDTO(BaseSchema):
    email: Optional[str] = Field(None, min_length=1, max_length=255)
    onboarded: Optional[bool] = None
    profile: Optional[dict] = None
    notification_preferences: Optional[dict] = None


class UserDTO(UserBase):
    id: UUID
    onboarded: bool
    profile: Optional[dict] = None
    notification_preferences: Optional[dict] = None
    created_at: datetime
