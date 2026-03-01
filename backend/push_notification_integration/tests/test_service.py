"""Tests for Push Notification Service."""

import pytest
import os
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from ..service import PushNotificationService
from ..models import (
    SendPushNotificationRequest,
    NotificationPayload,
    NotificationActionButton,
    NotificationAction,
    PushSubscription,
    PushSubscriptionKeys,
    SubscriptionRecord,
)


@pytest.fixture
def push_service():
    """Create push service instance with mock VAPID keys."""
    with patch.dict(os.environ, {
        "VAPID_PRIVATE_KEY": "test_private_key",
        "VAPID_PUBLIC_KEY": "test_public_key",
        "VAPID_CLAIMS_EMAIL": "mailto:test@example.com"
    }):
        return PushNotificationService()


@pytest.fixture
def sample_subscription():
    """Sample push subscription."""
    return PushSubscription(
        endpoint="https://fcm.googleapis.com/fcm/send/test",
        keys=PushSubscriptionKeys(
            p256dh="test_p256dh_key",
            auth="test_auth_secret"
        )
    )


@pytest.fixture
def sample_notification():
    """Sample notification payload."""
    return NotificationPayload(
        title="Test Notification",
        body="This is a test notification",
        task_id="task123",
        actions=[
            NotificationActionButton(
                action=NotificationAction.ACKNOWLEDGE,
                title="Done"
            ),
            NotificationActionButton(
                action=NotificationAction.SNOOZE,
                title="Snooze"
            )
        ]
    )


@pytest.mark.asyncio
async def test_subscribe(push_service, sample_subscription):
    """Test subscription registration."""
    subscription_record = SubscriptionRecord(
        user_id="user123",
        device_id="device456",
        device_name="Chrome on MacOS",
        subscription=sample_subscription,
    )

    success = await push_service.subscribe(subscription_record)
    assert success is True
    assert "user123" in push_service.subscriptions
    assert len(push_service.subscriptions["user123"]) == 1


@pytest.mark.asyncio
async def test_unsubscribe(push_service, sample_subscription):
    """Test subscription removal."""
    subscription_record = SubscriptionRecord(
        user_id="user123",
        device_id="device456",
        subscription=sample_subscription,
    )

    await push_service.subscribe(subscription_record)
    success = await push_service.unsubscribe("user123", "device456")

    assert success is True
    assert len(push_service.subscriptions["user123"]) == 0


@pytest.mark.asyncio
@patch("scrum_41_push_notification_integration.service.webpush")
async def test_send_push_notification(mock_webpush, push_service, sample_subscription, sample_notification):
    """Test sending push notification."""
    # Setup
    subscription_record = SubscriptionRecord(
        user_id="user123",
        device_id="device456",
        subscription=sample_subscription,
    )
    await push_service.subscribe(subscription_record)

    request = SendPushNotificationRequest(
        user_id="user123",
        notification=sample_notification,
        ttl=3600,
    )

    # Execute
    response = await push_service.send_push_notification(request)

    # Verify
    assert response.success is True
    assert response.sent_to == 1
    assert response.failed == 0
    assert mock_webpush.called


@pytest.mark.asyncio
async def test_send_push_no_subscriptions(push_service, sample_notification):
    """Test sending notification when user has no subscriptions."""
    request = SendPushNotificationRequest(
        user_id="nonexistent_user",
        notification=sample_notification,
    )

    response = await push_service.send_push_notification(request)

    assert response.success is False
    assert response.sent_to == 0
    assert "No active subscriptions" in response.message


def test_get_vapid_public_key(push_service):
    """Test retrieving VAPID public key."""
    public_key = push_service.get_vapid_public_key()
    assert public_key == "test_public_key"


@pytest.mark.asyncio
async def test_get_user_subscriptions(push_service, sample_subscription):
    """Test retrieving user subscriptions."""
    subscription_record = SubscriptionRecord(
        user_id="user123",
        device_id="device456",
        subscription=sample_subscription,
    )
    await push_service.subscribe(subscription_record)

    subscriptions = await push_service.get_user_subscriptions("user123")

    assert len(subscriptions) == 1
    assert subscriptions[0].device_id == "device456"


@pytest.mark.asyncio
async def test_cleanup_expired_subscriptions(push_service, sample_subscription):
    """Test cleaning up expired subscriptions."""
    # Create active and inactive subscriptions
    active_sub = SubscriptionRecord(
        user_id="user123",
        device_id="device1",
        subscription=sample_subscription,
        is_active=True,
    )
    inactive_sub = SubscriptionRecord(
        user_id="user123",
        device_id="device2",
        subscription=sample_subscription,
        is_active=False,
    )

    await push_service.subscribe(active_sub)
    await push_service.subscribe(inactive_sub)

    cleaned = await push_service.cleanup_expired_subscriptions()

    assert cleaned == 1
    subscriptions = await push_service.get_user_subscriptions("user123")
    assert len(subscriptions) == 1
    assert subscriptions[0].device_id == "device1"
