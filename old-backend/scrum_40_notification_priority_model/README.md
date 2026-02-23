# Notification Priority Model API

## SCRUM-40: Notification Priority Model

### Overview
This API implements a notification priority and escalation system for the Flux Life Assistant platform. It determines the appropriate escalation path based on notification priority levels and applies configurable escalation speed multipliers.

### Owner
**BE-B** | **Points:** 2 | **Component:** backend, notifications

---

## Features

### Priority Levels
Each notification has a priority field with three levels:

1. **Standard** - Basic notifications, push only
2. **Important** - Push → WhatsApp (after 2 min if no acknowledgment)
3. **Must-Not-Miss** - Push → WhatsApp (2 min) → Call (7 min)

### Escalation Rules

#### Standard Priority
- **Channel:** Push notification only
- **Wait Time:** N/A (no escalation)

#### Important Priority
- **Step 1:** Push notification (immediate)
- **Step 2:** WhatsApp message (after 2 minutes if no acknowledgment)

#### Must-Not-Miss Priority
- **Step 1:** Push notification (immediate)
- **Step 2:** WhatsApp message (after 2 minutes if no acknowledgment)
- **Step 3:** Phone call (after 7 minutes total if no acknowledgment)

### Escalation Speed Multiplier

The `escalation_speed_multiplier` parameter controls how quickly escalation occurs:

- **1x** (Normal): Standard wait times
- **5x** (Fast): 5 times faster (e.g., 2 min → 24 seconds)
- **10x** (Ultra Fast): 10 times faster (e.g., 2 min → 12 seconds)

**Example:** With a 10x multiplier:
- 2-minute wait → 12 seconds
- 7-minute wait → 42 seconds

---

## API Endpoints

### 1. Send Notification
**POST** `/api/v1/notifications/priority/send`

Send a notification with specified priority and escalation settings.

**Request Body:**
```json
{
  "user_id": "user123",
  "priority": "must_not_miss",
  "escalation_speed_multiplier": 10.0,
  "message": "Important task reminder",
  "metadata": {
    "task_id": "task_456"
  }
}
```

**Response:**
```json
{
  "notification_id": "uuid-here",
  "user_id": "user123",
  "priority": "must_not_miss",
  "escalation_path": {
    "priority": "must_not_miss",
    "steps": [
      {"channel": "push", "wait_time_seconds": 0},
      {"channel": "whatsapp", "wait_time_seconds": 120},
      {"channel": "call", "wait_time_seconds": 420}
    ]
  },
  "actual_wait_times": [0, 12, 42],
  "created_at": "2026-02-15T12:00:00Z",
  "status": "sent"
}
```

### 2. Get Escalation Configuration
**GET** `/api/v1/notifications/priority/config`

Retrieve the complete escalation configuration for all priority levels.

**Response:**
```json
{
  "standard": {
    "priority": "standard",
    "steps": [{"channel": "push", "wait_time_seconds": 0}]
  },
  "important": {
    "priority": "important",
    "steps": [
      {"channel": "push", "wait_time_seconds": 0},
      {"channel": "whatsapp", "wait_time_seconds": 120}
    ]
  },
  "must_not_miss": {
    "priority": "must_not_miss",
    "steps": [
      {"channel": "push", "wait_time_seconds": 0},
      {"channel": "whatsapp", "wait_time_seconds": 120},
      {"channel": "call", "wait_time_seconds": 420}
    ]
  }
}
```

### 3. Calculate Escalation Timing
**GET** `/api/v1/notifications/priority/timing`

Calculate detailed escalation timing for a specific priority and multiplier.

**Query Parameters:**
- `priority` (required): Priority level (standard/important/must_not_miss)
- `multiplier` (optional): Speed multiplier (default: 1.0)

**Example Request:**
```
GET /api/v1/notifications/priority/timing?priority=must_not_miss&multiplier=10.0
```

**Response:**
```json
{
  "priority": "must_not_miss",
  "multiplier": 10.0,
  "steps": [
    {
      "step_number": 1,
      "channel": "push",
      "base_wait_time_seconds": 0,
      "actual_wait_time_seconds": 0,
      "cumulative_time_seconds": 0,
      "time_from_start_human_readable": "0s"
    },
    {
      "step_number": 2,
      "channel": "whatsapp",
      "base_wait_time_seconds": 120,
      "actual_wait_time_seconds": 12,
      "cumulative_time_seconds": 12,
      "time_from_start_human_readable": "12s"
    },
    {
      "step_number": 3,
      "channel": "call",
      "base_wait_time_seconds": 420,
      "actual_wait_time_seconds": 42,
      "cumulative_time_seconds": 54,
      "time_from_start_human_readable": "54s"
    }
  ]
}
```

### 4. Health Check
**GET** `/api/v1/notifications/priority/health`

Check the health status of the notification priority service.

**Response:**
```json
{
  "status": "healthy",
  "service": "notification_priority_model",
  "version": "1.0.0"
}
```

---

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Import the router in your main FastAPI application:
```python
from backend.scrum_40_notification_priority_model import priority_router

app.include_router(priority_router)
```

---

## Usage Examples

### Example 1: Standard Priority Notification
```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/notifications/priority/send",
    json={
        "user_id": "user123",
        "priority": "standard",
        "escalation_speed_multiplier": 1.0,
        "message": "Daily task reminder"
    }
)
print(response.json())
```

### Example 2: Urgent Must-Not-Miss with 10x Speed
```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/notifications/priority/send",
    json={
        "user_id": "user456",
        "priority": "must_not_miss",
        "escalation_speed_multiplier": 10.0,
        "message": "URGENT: Critical task requires immediate attention",
        "metadata": {
            "task_id": "urgent_task_789",
            "severity": "critical"
        }
    }
)
print(response.json())
```

### Example 3: Check Timing Before Sending
```python
import requests

# Calculate timing first
timing = requests.get(
    "http://localhost:8000/api/v1/notifications/priority/timing",
    params={
        "priority": "important",
        "multiplier": 5.0
    }
)
print("Escalation timing:", timing.json())

# Then send notification
response = requests.post(
    "http://localhost:8000/api/v1/notifications/priority/send",
    json={
        "user_id": "user789",
        "priority": "important",
        "escalation_speed_multiplier": 5.0,
        "message": "Important meeting in 30 minutes"
    }
)
```

---

## Acceptance Criteria

✅ **Priority correctly determines escalation path**
- Standard: Push only
- Important: Push → WhatsApp (2 min)
- Must-Not-Miss: Push → WhatsApp (2 min) → Call (7 min)

✅ **Escalation speed multiplier correctly scales wait times**
- 1x: Normal timing
- 5x: Wait times divided by 5
- 10x: Wait times divided by 10 (e.g., 120s → 12s)

---

## Architecture

### Models (`models.py`)
- Pydantic models for type safety and validation
- Enums for priority levels, channels, and multipliers
- Request/response schemas

### Service (`service.py`)
- Business logic for escalation path determination
- Speed multiplier calculations
- Timing calculations and formatting

### Routes (`routes.py`)
- FastAPI endpoints
- Request validation
- Error handling

---

## Future Enhancements

- [ ] Integration with actual notification channels (Push, WhatsApp, Phone)
- [ ] Acknowledgment tracking system
- [ ] Automatic escalation triggers
- [ ] User preference management
- [ ] Notification history and analytics
- [ ] Rate limiting and throttling
- [ ] Retry mechanisms with exponential backoff

---

## Testing

Run tests with pytest:
```bash
pytest backend/scrum_40_notification_priority_model/tests/
```

---

## Related Components

- **SCRUM-39**: Notification Escalation Ladder (Parent story)
- **SCRUM-41**: Push Notification Integration
- **SCRUM-42**: WhatsApp Message Integration
- **SCRUM-43**: Phone Call Trigger

---

## License

Part of the Flux Life Assistant project.
