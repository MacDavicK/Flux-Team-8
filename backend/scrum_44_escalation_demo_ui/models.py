"""Data models for escalation notification demo"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum


class NotificationChannel(str, Enum):
    """Enum for notification channels"""
    PUSH = "push"
    WHATSAPP = "whatsapp"
    PHONE_CALL = "phone_call"


class EscalationSpeed(str, Enum):
    """Enum for escalation speed multipliers"""
    NORMAL = "1x"  # Real-time
    FAST = "5x"    # 5x faster
    ULTRA_FAST = "10x"  # 10x faster


class NotificationStatus(str, Enum):
    """Enum for notification status"""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    ACKNOWLEDGED = "acknowledged"


@dataclass
class NotificationStep:
    """Represents a single step in the escalation flow"""
    id: str
    channel: NotificationChannel
    delay_seconds: int  # Delay before this step executes
    status: NotificationStatus = NotificationStatus.PENDING
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "channel": self.channel.value,
            "delay_seconds": self.delay_seconds,
            "status": self.status.value,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "delivered_at": self.delivered_at.isoformat() if self.delivered_at else None,
            "error_message": self.error_message,
            "metadata": self.metadata
        }


@dataclass
class EscalationEvent:
    """Represents an escalation event with multiple notification steps"""
    id: str
    user_id: str
    title: str
    message: str
    speed: EscalationSpeed = EscalationSpeed.NORMAL
    created_at: datetime = None
    steps: list[NotificationStep] = None
    current_step_index: int = 0
    is_complete: bool = False
    is_acknowledged: bool = False

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.steps is None:
            self.steps = self._create_default_steps()

    def _create_default_steps(self) -> list[NotificationStep]:
        """Create default escalation steps based on best practices"""
        # Step delays are in seconds (will be adjusted by speed multiplier)
        base_steps = [
            NotificationStep(
                id=f"{self.id}_push",
                channel=NotificationChannel.PUSH,
                delay_seconds=0,  # Immediate
            ),
            NotificationStep(
                id=f"{self.id}_whatsapp",
                channel=NotificationChannel.WHATSAPP,
                delay_seconds=60,  # After 1 minute
            ),
            NotificationStep(
                id=f"{self.id}_call",
                channel=NotificationChannel.PHONE_CALL,
                delay_seconds=180,  # After 3 minutes total
            ),
        ]
        return base_steps

    def get_adjusted_delay(self, delay_seconds: int) -> float:
        """Get delay adjusted for speed multiplier"""
        speed_multipliers = {
            EscalationSpeed.NORMAL: 1.0,
            EscalationSpeed.FAST: 0.2,  # 5x faster = 1/5 time
            EscalationSpeed.ULTRA_FAST: 0.1,  # 10x faster = 1/10 time
        }
        multiplier = speed_multipliers.get(self.speed, 1.0)
        return delay_seconds * multiplier

    def get_current_step(self) -> Optional[NotificationStep]:
        """Get the current step to execute"""
        if self.current_step_index < len(self.steps):
            return self.steps[self.current_step_index]
        return None

    def advance_step(self) -> bool:
        """Move to the next step. Returns True if more steps remain."""
        self.current_step_index += 1
        if self.current_step_index >= len(self.steps):
            self.is_complete = True
            return False
        return True

    def acknowledge(self):
        """Mark the escalation as acknowledged by the user"""
        self.is_acknowledged = True
        self.is_complete = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "message": self.message,
            "speed": self.speed.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "steps": [step.to_dict() for step in self.steps],
            "current_step_index": self.current_step_index,
            "is_complete": self.is_complete,
            "is_acknowledged": self.is_acknowledged
        }