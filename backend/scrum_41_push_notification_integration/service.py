"""Business logic for Push Notification Integration.

Handles push notification delivery, subscription management, and VAPID configuration.
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from pywebpush import webpush, WebPushException
from py_vapid import Vapid

from .models import (
    PushSubscription,
    NotificationPayload,
    SubscriptionRecord,
    SendPushNotificationRequest,
    PushNotificationResponse,
)

logger = logging.getLogger(__name__)


class PushNotificationService:
    """Service for managing web push notifications."""

    def __init__(self):
        """Initialize push notification service with VAPID keys."""
        self.vapid_private_key = os.getenv("VAPID_PRIVATE_KEY")
        self.vapid_public_key = os.getenv("VAPID_PUBLIC_KEY")
        self.vapid_claims_email = os.getenv(
            "VAPID_CLAIMS_EMAIL",
            "mailto:support@fluxassistant.com"
        )

        if not self.vapid_private_key or not self.vapid_public_key:
            raise ValueError(
                "VAPID keys not configured. Set VAPID_PRIVATE_KEY and "
                "VAPID_PUBLIC_KEY environment variables."
            )

        # In-memory subscription store (replace with database in production)
        self.subscriptions: Dict[str, List[SubscriptionRecord]] = {}

    def get_vapid_public_key(self) -> str:
        """Get VAPID public key for client-side subscription.

        Returns:
            Base64 URL-encoded VAPID public key
        """
        return self.vapid_public_key

    async def subscribe(self, subscription_data: SubscriptionRecord) -> bool:
        """Register a new push notification subscription.

        Args:
            subscription_data: Subscription details including user_id, device_id, and push subscription

        Returns:
            True if subscription was registered successfully
        """
        try:
            user_id = subscription_data.user_id

            if user_id not in self.subscriptions:
                self.subscriptions[user_id] = []

            # Check if device already subscribed, update if exists
            existing = next(
                (s for s in self.subscriptions[user_id]
                 if s.device_id == subscription_data.device_id),
                None
            )

            if existing:
                existing.subscription = subscription_data.subscription
                existing.updated_at = datetime.utcnow()
                existing.is_active = True
                logger.info(
                    f"Updated subscription for user {user_id}, device {subscription_data.device_id}"
                )
            else:
                self.subscriptions[user_id].append(subscription_data)
                logger.info(
                    f"New subscription for user {user_id}, device {subscription_data.device_id}"
                )

            return True

        except Exception as e:
            logger.error(f"Failed to register subscription: {e}")
            return False

    async def unsubscribe(self, user_id: str, device_id: str) -> bool:
        """Remove a push notification subscription.

        Args:
            user_id: User identifier
            device_id: Device identifier to unsubscribe

        Returns:
            True if subscription was removed
        """
        try:
            if user_id in self.subscriptions:
                self.subscriptions[user_id] = [
                    s for s in self.subscriptions[user_id]
                    if s.device_id != device_id
                ]
                logger.info(f"Unsubscribed device {device_id} for user {user_id}")
                return True
            return False

        except Exception as e:
            logger.error(f"Failed to unsubscribe: {e}")
            return False

    def _build_push_payload(self, notification: NotificationPayload) -> str:
        """Build Web Push notification payload.

        Args:
            notification: Notification content and metadata

        Returns:
            JSON string of notification payload
        """
        payload = {
            "title": notification.title,
            "body": notification.body,
            "icon": notification.icon,
            "badge": notification.badge,
            "image": notification.image,
            "tag": notification.tag,
            "requireInteraction": notification.require_interaction,
            "silent": notification.silent,
            "data": notification.data or {},
        }

        # Add action buttons
        if notification.actions:
            payload["actions"] = [
                {
                    "action": action.action.value,
                    "title": action.title,
                    "icon": action.icon,
                }
                for action in notification.actions
            ]

        # Add task_id to data if present
        if notification.task_id:
            payload["data"]["task_id"] = notification.task_id

        return json.dumps(payload)

    async def send_push_notification(
        self,
        request: SendPushNotificationRequest
    ) -> PushNotificationResponse:
        """Send push notification to all user's subscribed devices.

        Args:
            request: Push notification request with user_id and notification content

        Returns:
            Response with delivery status
        """
        user_id = request.user_id
        notification = request.notification
        ttl = request.ttl
        topic = request.topic

        if user_id not in self.subscriptions or not self.subscriptions[user_id]:
            logger.warning(f"No subscriptions found for user {user_id}")
            return PushNotificationResponse(
                success=False,
                sent_to=0,
                failed=0,
                message=f"No active subscriptions for user {user_id}",
            )

        payload = self._build_push_payload(notification)
        sent_count = 0
        failed_count = 0
        device_results = []

        for subscription_record in self.subscriptions[user_id]:
            if not subscription_record.is_active:
                continue

            try:
                subscription_info = subscription_record.subscription.model_dump()

                # Send push notification using pywebpush
                webpush(
                    subscription_info=subscription_info,
                    data=payload,
                    vapid_private_key=self.vapid_private_key,
                    vapid_claims={
                        "sub": self.vapid_claims_email,
                    },
                    ttl=ttl,
                    topic=topic,
                    urgency=notification.urgency,
                )

                subscription_record.last_used_at = datetime.utcnow()
                sent_count += 1

                device_results.append({
                    "device_id": subscription_record.device_id,
                    "status": "success",
                    "message": "Notification sent successfully",
                })

                logger.info(
                    f"Sent push notification to user {user_id}, "
                    f"device {subscription_record.device_id}"
                )

            except WebPushException as e:
                failed_count += 1
                error_msg = str(e)

                device_results.append({
                    "device_id": subscription_record.device_id,
                    "status": "failed",
                    "error": error_msg,
                })

                # Handle expired or invalid subscriptions
                if e.response and e.response.status_code in [404, 410]:
                    subscription_record.is_active = False
                    logger.warning(
                        f"Subscription expired for user {user_id}, "
                        f"device {subscription_record.device_id}"
                    )
                else:
                    logger.error(
                        f"Failed to send push to user {user_id}, "
                        f"device {subscription_record.device_id}: {error_msg}"
                    )

            except Exception as e:
                failed_count += 1
                error_msg = str(e)

                device_results.append({
                    "device_id": subscription_record.device_id,
                    "status": "error",
                    "error": error_msg,
                })

                logger.error(
                    f"Unexpected error sending push to user {user_id}, "
                    f"device {subscription_record.device_id}: {error_msg}"
                )

        success = sent_count > 0
        message = (
            f"Sent to {sent_count} device(s)" if success
            else f"Failed to send to all devices ({failed_count} failed)"
        )

        return PushNotificationResponse(
            success=success,
            sent_to=sent_count,
            failed=failed_count,
            message=message,
            device_results=device_results,
        )

    async def get_user_subscriptions(self, user_id: str) -> List[SubscriptionRecord]:
        """Get all active subscriptions for a user.

        Args:
            user_id: User identifier

        Returns:
            List of active subscription records
        """
        if user_id not in self.subscriptions:
            return []

        return [
            s for s in self.subscriptions[user_id]
            if s.is_active
        ]

    async def cleanup_expired_subscriptions(self) -> int:
        """Remove expired or inactive subscriptions.

        Returns:
            Number of subscriptions cleaned up
        """
        cleaned_count = 0

        for user_id in self.subscriptions:
            active_subs = [
                s for s in self.subscriptions[user_id]
                if s.is_active
            ]
            cleaned = len(self.subscriptions[user_id]) - len(active_subs)
            cleaned_count += cleaned

            if cleaned > 0:
                self.subscriptions[user_id] = active_subs
                logger.info(
                    f"Cleaned up {cleaned} expired subscription(s) for user {user_id}"
                )

        return cleaned_count
