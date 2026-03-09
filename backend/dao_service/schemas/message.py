"""Pydantic DTOs for the messages entity."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import ConfigDict, Field, field_validator

from dao_service.schemas.base import BaseSchema

ROLE_VALUES = {"user", "assistant", "system", "function"}
INPUT_MODALITY_VALUES = {"voice", "text"}


class MessageBase(BaseSchema):
    """Shared message attributes."""

    role: str
    content: str = Field(..., min_length=1)
    input_modality: str = "text"
    metadata: Optional[dict] = Field(default_factory=dict, validation_alias="metadata_")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: str) -> str:
        if value not in ROLE_VALUES:
            raise ValueError(f"role must be one of: {sorted(ROLE_VALUES)}")
        return value

    @field_validator("input_modality")
    @classmethod
    def validate_input_modality(cls, value: str) -> str:
        if value not in INPUT_MODALITY_VALUES:
            raise ValueError(f"input_modality must be one of: {sorted(INPUT_MODALITY_VALUES)}")
        return value


class MessageCreateDTO(MessageBase):
    """For creation requests."""

    conversation_id: UUID


class MessageUpdateDTO(BaseSchema):
    """For updates -- only role and content are updatable."""

    role: Optional[str] = None
    content: Optional[str] = None

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and value not in ROLE_VALUES:
            raise ValueError(f"role must be one of: {sorted(ROLE_VALUES)}")
        return value


class MessageDTO(MessageBase):
    """Complete response schema."""

    id: UUID
    conversation_id: UUID
    created_at: datetime
