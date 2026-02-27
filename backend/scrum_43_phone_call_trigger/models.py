"""Data models for phone call trigger API."""

from typing import Optional
from pydantic import BaseModel, Field, validator
from datetime import datetime


class CallRequest(BaseModel):
    """Request model for initiating a phone call."""
    
    phone_number: str = Field(
        ...,
        description="Phone number to call in E.164 format (e.g., +14155551234)",
        example="+14155551234"
    )
    task_title: str = Field(
        ...,
        description="Title of the critical task for TTS message",
        example="Submit quarterly report"
    )
    task_id: Optional[str] = Field(
        None,
        description="Optional task ID for tracking acknowledgment"
    )
    
    @validator('phone_number')
    def validate_phone_number(cls, v):
        """Validate phone number is in E.164 format."""
        if not v.startswith('+'):
            raise ValueError('Phone number must be in E.164 format starting with +')
        if len(v) < 10:
            raise ValueError('Phone number is too short')
        return v


class CallResponse(BaseModel):
    """Response model for call initiation."""
    
    call_sid: str = Field(..., description="Twilio Call SID")
    status: str = Field(..., description="Call status")
    to: str = Field(..., description="Destination phone number")
    message: str = Field(..., description="Status message")
    initiated_at: datetime = Field(default_factory=datetime.utcnow)


class GatherResponse(BaseModel):
    """Response model for handling gathered input from Twilio."""
    
    call_sid: str = Field(..., description="Twilio Call SID")
    digits: Optional[str] = Field(None, description="Digits pressed by user")
    task_id: Optional[str] = Field(None, description="Associated task ID")
    acknowledged: bool = Field(False, description="Whether task was acknowledged")
    processed_at: datetime = Field(default_factory=datetime.utcnow)
