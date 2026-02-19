"""Data models for Push Notification Integration.

Defines Pydantic models for push notification subscriptions, payloads, and responses.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, HttpUrl
from enum import Enum


class NotificationAction(str, Enum):
    """Supported notification actions."""
    ACKNOWLEDGE = "acknowledge"
    SNOOZE = "snooze"
    VIEW = "view"
    DISMISS = "dismiss"


class PushSubscriptionKeys(BaseModel):
    """Encryption keys for push subscription."""
    p256dh: str = Field(..., description="P-256 ECDH public key")
    auth: str = Field(..., description="Authentication secret")


class PushSubscription(BaseModel):
    """Web Push API subscription information."""
    endpoint: HttpUrl = Field(..., description="Push service endpoint URL")
    keys: PushSubscriptionKeys = Field(..., description="Encryption keys")
    expiration_time: Optional[int] = Field(None, description="Subscription expiration timestamp")


class SubscribeRequest(BaseModel):
    """Request to register a push notification subscription."""
    user_id: str = Field(..., description="Unique user identifier")
    subscription: PushSubscription = Field(..., description="Push subscription details")
    device_id: str = Field(..., description="Unique device identifier")
    device_name: Optional[str] = Field(None, description="Human-readable device name")
    user_agent: Optional[str] = Field(None, description="Browser user agent string")


class UnsubscribeRequest(BaseModel):
    """Request to remove a push notification subscription."""
    user_id: str = Field(..., description="Unique user identifier")
    device_id: str = Field(..., description="Unique device identifier")


class NotificationActionButton(BaseModel):
    """Action button configuration for notification."""
    action: NotificationAction = Field(..., description="Action identifier")
    title: str = Field(..., description="Button text")
    icon: Optional[str] = Field(None, description="Button icon URL")


class NotificationPayload(BaseModel):
    """Notification content and metadata."""
    title: str = Field(..., max_length=100, description="Notification title")
    body: str = Field(..., max_length=200, description="Notification body text")
    task_id: Optional[str] = Field(None, description="Associated task ID")
    icon: Optional[str] = Field(None, description="Notification icon URL")
    badge: Optional[str] = Field(None, description="Badge icon URL")
    image: Optional[str] = Field(None, description="Notification image URL")
    actions: List[NotificationActionButton] = Field(
        default_factory=list,
        max_length=4,
        description="Action buttons (max 4)"
    )
    data: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional custom data"
    )
    tag: Optional[str] = Field(None, description="Notification tag for grouping")
    require_interaction: bool = Field(
        False,
        description="Keep notification visible until user interacts"
    )
    silent: bool = Field(False, description="Silent notification (no sound/vibration)")
    urgency: str = Field(
        "normal",
        description="Notification urgency (very-low, low, normal, high)"
    )


class SendPushNotificationRequest(BaseModel):
    """Request to send push notification to user."""
    user_id: str = Field(..., description="Target user ID")
    notification: NotificationPayload = Field(..., description="Notification content")
    ttl: int = Field(
        86400,
        ge=0,
        le=2419200,
        description="Time-to-live in seconds (default 24h, max 28 days)"
    )
    topic: Optional[str] = Field(None, description="Notification topic for collapsing")


class PushNotificationResponse(BaseModel):
    """Response from sending push notification."""
    success: bool = Field(..., description="Overall operation success")
    sent_to: int = Field(..., description="Number of devices successfully sent to")
    failed: int = Field(..., description="Number of failed deliveries")
    message: str = Field(..., description="Status message")
    device_results: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="Per-device delivery results"
    )


class VapidPublicKeyResponse(BaseModel):
    """Response containing VAPID public key."""
    public_key: str = Field(..., description="Base64 URL-encoded VAPID public key")


class NotificationActionResponse(BaseModel):
    """Response from handling a notification action."""
    success: bool = Field(..., description="Action processed successfully")
    action: NotificationAction = Field(..., description="Action that was processed")
    message: str = Field(..., description="Result message")
    task_id: Optional[str] = Field(None, description="Associated task ID")


class SubscriptionRecord(BaseModel):
    """Database record for push subscription."""
    id: Optional[str] = Field(None, description="Record ID")
    user_id: str = Field(..., description="User ID")
    device_id: str = Field(..., description="Device ID")
    device_name: Optional[str] = Field(None, description="Device name")
    subscription: PushSubscription = Field(..., description="Subscription data")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_used_at: Optional[datetime] = Field(None, description="Last successful push")
    is_active: bool = Field(True, description="Subscription is active")
    user_agent: Optional[str] = Field(None, description="Browser user agent")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
