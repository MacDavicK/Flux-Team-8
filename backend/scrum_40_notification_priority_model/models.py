"""
Data models for Notification Priority
"""
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, validator
from datetime import datetime


class NotificationPriority(str, Enum):
    """Priority levels for notifications"""
    STANDARD = "standard"
    IMPORTANT = "important"
    MUST_NOT_MISS = "must_not_miss"


class EscalationChannel(str, Enum):
    """Available notification channels for escalation"""
    PUSH = "push"
    WHATSAPP = "whatsapp"
    CALL = "call"


class EscalationSpeedMultiplier(float, Enum):
    """Speed multipliers for escalation timing"""
    NORMAL = 1.0
    FAST = 5.0
    ULTRA_FAST = 10.0


class EscalationStep(BaseModel):
    """Represents a single step in the escalation ladder"""
    channel: EscalationChannel
    wait_time_seconds: int = Field(..., description="Time to wait before escalating if no acknowledgment")
    
    class Config:
        use_enum_values = True


class EscalationPath(BaseModel):
    """Complete escalation path for a notification priority"""
    priority: NotificationPriority
    steps: List[EscalationStep]
    
    class Config:
        use_enum_values = True


class NotificationRequest(BaseModel):
    """Request to send a notification with priority"""
    user_id: str = Field(..., description="ID of the user to notify")
    priority: NotificationPriority = Field(default=NotificationPriority.STANDARD)
    escalation_speed_multiplier: float = Field(
        default=1.0,
        ge=1.0,
        le=10.0,
        description="Multiplier to reduce wait times (1x, 5x, or 10x)"
    )
    message: str = Field(..., description="Notification message content")
    metadata: Optional[dict] = Field(default=None, description="Additional metadata")
    
    @validator('escalation_speed_multiplier')
    def validate_multiplier(cls, v):
        """Ensure multiplier is one of the valid values"""
        valid_multipliers = [1.0, 5.0, 10.0]
        if v not in valid_multipliers:
            raise ValueError(f"Escalation speed multiplier must be one of {valid_multipliers}")
        return v
    
    class Config:
        use_enum_values = True


class NotificationResponse(BaseModel):
    """Response after sending a notification"""
    notification_id: str
    user_id: str
    priority: NotificationPriority
    escalation_path: EscalationPath
    actual_wait_times: List[int] = Field(
        description="Actual wait times in seconds after applying multiplier"
    )
    created_at: datetime
    status: str = "sent"
    
    class Config:
        use_enum_values = True


class EscalationConfig(BaseModel):
    """Configuration for all priority levels"""
    standard: EscalationPath
    important: EscalationPath
    must_not_miss: EscalationPath
    
    class Config:
        use_enum_values = True
