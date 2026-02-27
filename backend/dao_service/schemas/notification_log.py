"""Notification log DTOs."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import field_validator

from dao_service.schemas.base import BaseSchema

CHANNEL_VALUES = {"push", "whatsapp", "call"}


class NotificationLogBase(BaseSchema):
    channel: str
    sent_at: Optional[datetime] = None
    response: Optional[str] = None
    responded_at: Optional[datetime] = None

    @field_validator("channel")
    @classmethod
    def validate_channel(cls, value: str) -> str:
        if value not in CHANNEL_VALUES:
            raise ValueError(f"channel must be one of: {sorted(CHANNEL_VALUES)}")
        return value


class NotificationLogCreateDTO(NotificationLogBase):
    task_id: UUID


class NotificationLogUpdateDTO(BaseSchema):
    channel: Optional[str] = None
    sent_at: Optional[datetime] = None
    response: Optional[str] = None
    responded_at: Optional[datetime] = None

    @field_validator("channel")
    @classmethod
    def validate_channel(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and value not in CHANNEL_VALUES:
            raise ValueError(f"channel must be one of: {sorted(CHANNEL_VALUES)}")
        return value


class NotificationLogDTO(NotificationLogBase):
    id: UUID
    task_id: UUID
