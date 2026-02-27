# Escalation Demo UI (SCRUM-44)

## Overview

This module provides a Python-based REST API for the Escalation Demo UI feature. It implements a multi-channel notification escalation system that progressively sends notifications through different channels (Push → WhatsApp → Phone Call) with configurable speed multipliers for demonstration purposes.

## Features

- **Multi-Channel Escalation**: Automatically escalates notifications through:
  - Push Notification (immediate)
  - WhatsApp Message (after 1 minute)
  - Phone Call (after 3 minutes)
- **Speed Control**: Support for 1x, 5x, and 10x speed multipliers for demo purposes
- **Real-time Status Tracking**: Monitor escalation progress through the API
- **Acknowledgment System**: Stop escalation when user acknowledges
- **Async Processing**: Non-blocking escalation flows using asyncio

## Architecture

The API follows a layered architecture:

```
├── models.py       # Data models and enums
├── service.py      # Business logic layer
├── routes.py       # REST API endpoints
└── __init__.py     # Module exports
```

### Key Components

#### Models
- `EscalationEvent`: Represents a complete escalation flow
- `NotificationStep`: Individual notification in the escalation chain
- `NotificationChannel`: Enum for notification channels (PUSH, WHATSAPP, PHONE_CALL)
- `EscalationSpeed`: Speed multipliers (1x, 5x, 10x)
- `NotificationStatus`: Status tracking for each notification

#### Service Layer
- `EscalationDemoService`: Core business logic
  - Creates and manages escalation events
  - Executes async escalation flows
  - Handles notification sending (simulated)
  - Manages acknowledgments and cancellations

#### API Routes
All endpoints are prefixed with `/api/escalation-demo`

## API Endpoints

### Health Check
```
GET /api/escalation-demo/health
```
Check service health status.

### Trigger Escalation
```
POST /api/escalation-demo/trigger
Content-Type: application/json

{
  "user_id": "user123",
  "title": "Critical Alert",
  "message": "Action required: System outage detected",
  "speed": "5x"  // Optional: "1x", "5x", or "10x"
}
```

Response:
```json
{
  "success": true,
  "escalation": {
    "id": "escalation-uuid",
    "user_id": "user123",
    "title": "Critical Alert",
    "message": "Action required: System outage detected",
    "speed": "5x",
    "created_at": "2026-02-15T13:00:00Z",
    "steps": [...],
    "current_step_index": 0,
    "is_complete": false,
    "is_acknowledged": false
  }
}
```

### Get Escalation Status
```
GET /api/escalation-demo/escalations/{escalation_id}
```

Returns detailed status of an escalation including whether it's still running.

### List Escalations
```
GET /api/escalation-demo/escalations?user_id={user_id}
```

List all escalations, optionally filtered by user ID.

### Acknowledge Escalation
```
POST /api/escalation-demo/escalations/{escalation_id}/acknowledge
```

Mark an escalation as acknowledged and stop further notifications.

### Cancel Escalation
```
POST /api/escalation-demo/escalations/{escalation_id}/cancel
```

Cancel an ongoing escalation flow.

## Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

## Usage

### Integrating with Flask App

```python
from flask import Flask
from backend.scrum_44_escalation_demo_ui import escalation_demo_bp

app = Flask(__name__)
app.register_blueprint(escalation_demo_bp)

if __name__ == '__main__':
    app.run(debug=True)
```

### Example: Triggering an Escalation

```python
import requests

response = requests.post(
    'http://localhost:5000/api/escalation-demo/trigger',
    json={
        'user_id': 'user123',
        'title': 'Task Reminder',
        'message': 'Don\'t forget your daily check-in!',
        'speed': '10x'  # For fast demo
    }
)

escalation = response.json()['escalation']
escalation_id = escalation['id']

print(f"Escalation started: {escalation_id}")
```

## Escalation Flow

1. **Initial Trigger**: Client calls `/trigger` endpoint
2. **Immediate Push**: Push notification sent immediately
3. **Wait Period**: System waits (adjusted by speed multiplier)
4. **WhatsApp Message**: Sent if not acknowledged
5. **Wait Period**: System waits again
6. **Phone Call**: Final escalation step if still not acknowledged
7. **Complete**: Escalation marked as complete

### Speed Multipliers

- **1x (Normal)**: Real-time delays (1 min → WhatsApp, 3 min → Call)
- **5x (Fast)**: 5× faster (12 sec → WhatsApp, 36 sec → Call)
- **10x (Ultra Fast)**: 10× faster (6 sec → WhatsApp, 18 sec → Call)

## Testing

The module includes simulated notification sending. In production, these would integrate with:
- Push Notification Services (Firebase, OneSignal, etc.)
- WhatsApp Business API
- Telephony APIs (Twilio, Vonage, etc.)

## Integration Points

For production deployment, implement actual notification services:

```python
# In service.py, replace simulated methods:
async def _send_push_notification(self, escalation, step):
    # TODO: Integrate with Firebase Cloud Messaging
    pass

async def _send_whatsapp_notification(self, escalation, step):
    # TODO: Integrate with WhatsApp Business API
    pass

async def _send_phone_call(self, escalation, step):
    # TODO: Integrate with Twilio Voice API
    pass
```

## Design Principles

This implementation follows escalation best practices from industry research:

- **Progressive Escalation**: Start with less intrusive channels
- **Time-Based Triggers**: Automatic escalation after predetermined intervals
- **Acknowledgment Mechanism**: Stop escalation when user responds
- **Status Tracking**: Full visibility into escalation state
- **Async Processing**: Non-blocking operations for scalability

## Related SCRUM Tickets

- SCRUM-40: Notification Priority Model
- SCRUM-41: Push Notification Integration  
- SCRUM-43: Phone Call Trigger
- SCRUM-44: Escalation Demo UI (this module)

## Future Enhancements

- [ ] Persist escalation state to database
- [ ] WebSocket support for real-time status updates
- [ ] Custom escalation schedules per user
- [ ] Analytics and reporting dashboard
- [ ] Integration with actual notification services
- [ ] Retry mechanisms for failed notifications
- [ ] Multi-user escalation policies