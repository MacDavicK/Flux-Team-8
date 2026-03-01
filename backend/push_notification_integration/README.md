# Push Notification Integration API

> **Note:** This feature is documented in the main [Notification Escalation](../../docs/notification-escalation.md) guide. This file contains implementation-specific details for SCRUM-41.

## SCRUM-41: Push Notification Integration

**Owner:** BE-B · **Points:** 3 · **Component:** `notifications`

### Overview

This API implements web push notification functionality for the Flux Life Assistant platform. It integrates with the Web Push API standard to deliver real-time notifications to Progressive Web App (PWA) users, enabling timely task reminders and action prompts.

### Features

- **Web Push Protocol Support**: Standards-compliant implementation using VAPID authentication
- **Subscription Management**: Register, update, and manage push notification subscriptions
- **Rich Notifications**: Send notifications with task titles and interactive action buttons
- **Action Handling**: Support for Acknowledge and Snooze actions
- **Multi-Device Support**: Manage subscriptions across multiple user devices
- **Secure Delivery**: VAPID-based authentication for secure push message delivery

### API Endpoints

#### POST `/notifications/push`
Sends a push notification to a user's subscribed device(s).

**Request Body:**
```json
{
  "user_id": "string",
  "notification": {
    "title": "string",
    "body": "string",
    "task_id": "string",
    "actions": [
      {"action": "acknowledge", "title": "Acknowledge"},
      {"action": "snooze", "title": "Snooze"}
    ]
  }
}
```

**Response:**
```json
{
  "success": true,
  "sent_to": 2,
  "failed": 0,
  "message": "Push notification sent successfully"
}
```

#### POST `/notifications/push/subscribe`
Registers a new push notification subscription for a user.

**Request Body:**
```json
{
  "user_id": "string",
  "subscription": {
    "endpoint": "string",
    "keys": {
      "p256dh": "string",
      "auth": "string"
    }
  },
  "device_id": "string"
}
```

#### DELETE `/notifications/push/unsubscribe`
Removes a push notification subscription.

**Request Body:**
```json
{
  "user_id": "string",
  "device_id": "string"
}
```

#### GET `/notifications/push/vapid-public-key`
Returns the VAPID public key for client-side subscription setup.

**Response:**
```json
{
  "public_key": "string"
}
```

### Acceptance Criteria

✅ PWA receives push notifications when browser is open  
✅ Notification shows task title and action buttons  
✅ Clicking "Acknowledge" calls API to mark notification as acknowledged  
✅ Support for "Snooze" action with configurable delay  
✅ Multi-device subscription management

### Architecture

**Components:**
- `models.py`: Data models for subscriptions and notifications
- `service.py`: Business logic for push notification delivery
- `routes.py`: FastAPI endpoint definitions
- `tests/`: Unit and integration tests

**Dependencies:**
- `pywebpush`: Python library for Web Push protocol
- `py-vapid`: VAPID key generation and JWT signing
- `cryptography`: Encryption for secure message delivery

### Configuration

Environment variables required:
```
VAPID_PRIVATE_KEY=<base64-encoded-private-key>
VAPID_PUBLIC_KEY=<base64-encoded-public-key>
VAPID_CLAIMS_EMAIL=mailto:your-email@example.com
```

### Usage Example

```python
from scrum_41_push_notification_integration.service import PushNotificationService

service = PushNotificationService()

# Send push notification
await service.send_push_notification(
    user_id="user123",
    title="Task Reminder",
    body="Complete daily workout routine",
    task_id="task456",
    actions=[
        {"action": "acknowledge", "title": "Done"},
        {"action": "snooze", "title": "Remind me later"}
    ]
)
```

### Integration Points

- **Notification Priority Model (SCRUM-40)**: Uses priority levels to determine when push notifications are triggered
- **Notification Escalation Ladder**: First step in the escalation chain (Push → SMS → WhatsApp → Phone Call)
- **Task Management**: Integrates with task service for acknowledgment actions

### Testing

Run tests:
```bash
pytest backend/scrum_41_push_notification_integration/tests/
```

### Security Considerations

- VAPID keys must be securely stored and never exposed to clients
- Subscriptions are tied to authenticated user sessions
- Rate limiting applied to prevent notification spam
- Payload encryption follows Web Push encryption standards (RFC 8291)

### Browser Support

- Chrome 50+
- Firefox 44+
- Safari 16+
- Edge 79+
- Opera 37+
---

## Swagger / API Documentation

This module uses **FastAPI**, which provides automatic interactive API documentation via Swagger UI.

### Running the standalone API server

```bash
# From the backend/ directory
cd /workspaces/Flux-Team-8/backend
uvicorn scrum_41_push_notification_integration.main:app --host 0.0.0.0 --port 8041 --reload
```

### Accessing Swagger UI

| Interface | URL |
|---|---|
| **Swagger UI** (interactive) | `http://localhost:8041/docs` |
| **ReDoc** (read-only) | `http://localhost:8041/redoc` |
| **OpenAPI JSON spec** | `http://localhost:8041/openapi.json` |

Once running, open `http://localhost:8041/docs` in your browser to explore and test all endpoints interactively.

### Running via the main app

This module's router is also included in the main backend app. When running the full backend:

```bash
cd /workspaces/Flux-Team-8/backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

All `Push Notification Integration API` endpoints will be available at `http://localhost:8000/docs` alongside the other modules.
