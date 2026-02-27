"""
Data models for WhatsApp notification tracking
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from enum import Enum


class NotificationStatus(Enum):
    """Enum for notification status"""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    READ = "read"


@dataclass
class WhatsAppNotification:
    """Model for WhatsApp notification"""
    task_id: str
    task_title: str
    recipient_number: str
    message: str
    status: NotificationStatus = NotificationStatus.PENDING
    message_sid: Optional[str] = None
    created_at: datetime = None
    sent_at: Optional[datetime] = None
    error_message: Optional[str] = None
    app_link: Optional[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'task_id': self.task_id,
            'task_title': self.task_title,
            'recipient_number': self.recipient_number,
            'message': self.message,
            'status': self.status.value,
            'message_sid': self.message_sid,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'error_message': self.error_message,
            'app_link': self.app_link
        }
