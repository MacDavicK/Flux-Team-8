"""User DTOs."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import EmailStr, Field

from dao_service.schemas.base import BaseSchema


class UserBase(BaseSchema):
    name: str = Field(..., min_length=1, max_length=255)
    email: str = Field(..., min_length=1, max_length=255)


class UserCreateDTO(UserBase):
    preferences: Optional[dict] = Field(default_factory=dict)
    demo_mode: bool = False


class UserUpdateDTO(BaseSchema):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[str] = Field(None, min_length=1, max_length=255)
    preferences: Optional[dict] = None
    demo_mode: Optional[bool] = None


class UserDTO(UserBase):
    id: UUID
    preferences: Optional[dict] = None
    demo_mode: bool
    created_at: datetime
