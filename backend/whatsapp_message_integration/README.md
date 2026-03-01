# WhatsApp Message Integration (SCRUM-42)

> **Note:** This feature is documented in the main [Notification Escalation](../../docs/notification-escalation.md) guide. This file contains implementation-specific details for SCRUM-42.

## Overview

This module provides WhatsApp messaging integration for the Flux Life Assistant using the Twilio API. It enables sending task reminder notifications via WhatsApp with templated messages.

## Features

- Send WhatsApp messages via Twilio API (Sandbox or Business API)
- Templated message format: "Hey! Don't forget: {task_title} 🎯" with app link
- Comprehensive error handling and logging
- Message status tracking
- RESTful API endpoints
- Support for both Twilio Sandbox and WhatsApp Business API

## API Endpoints

### Send WhatsApp Message

**POST** `/notifications/whatsapp`

Send a WhatsApp notification for a task reminder.

#### Request Body

```json
{
  "task_id": "task-123",
  "task_title": "Complete project proposal",
  "recipient_number": "+15551234567",
  "custom_message": "Optional custom message" // Optional
}
```

#### Response (200 OK)

```json
{
  "success": true,
  "message": "WhatsApp message sent successfully",
  "data": {
    "task_id": "task-123",
    "task_title": "Complete project proposal",
    "recipient_number": "whatsapp:+15551234567",
    "message": "Hey! Don't forget: Complete project proposal 🎯\n\nhttps://flux-life-assistant.app/tasks/task-123",
    "status": "sent",
    "message_sid": "SM1234567890abcdef",
    "sent_at": "2026-02-15T21:00:00Z",
    "app_link": "https://flux-life-assistant.app/tasks/task-123"
  }
}
```

#### Error Response (500)

```json
{
  "success": false,
  "error": "Failed to send WhatsApp message",
  "details": "Twilio error: Invalid phone number (Code: 21211)"
}
```

### Get Message Status

**GET** `/notifications/whatsapp/status/<message_sid>`

Retrieve the delivery status of a sent WhatsApp message.

#### Response (200 OK)

```json
{
  "success": true,
  "data": {
    "sid": "SM1234567890abcdef",
    "status": "delivered",
    "date_sent": "2026-02-15T21:00:00Z",
    "date_updated": "2026-02-15T21:00:05Z",
    "error_code": null,
    "error_message": null
  }
}
```

### Health Check

**GET** `/notifications/whatsapp/health`

Check if the WhatsApp service is healthy.

#### Response (200 OK)

```json
{
  "status": "healthy",
  "service": "whatsapp"
}
```

## Environment Variables

The following environment variables must be configured:

```bash
# Required
TWILIO_ACCOUNT_SID=your_account_sid_here
TWILIO_AUTH_TOKEN=your_auth_token_here

# Optional (defaults provided)
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886  # Twilio sandbox number
APP_BASE_URL=https://flux-life-assistant.app
```

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Twilio

#### Option A: Twilio Sandbox (Development)

1. Go to [Twilio Console](https://console.twilio.com/)
2. Navigate to Messaging → Try it out → Send a WhatsApp message
3. Join the sandbox by sending the join code to the sandbox number
4. Use the sandbox number as `TWILIO_WHATSAPP_FROM`

#### Option B: WhatsApp Business API (Production)

1. Set up WhatsApp Business API in Twilio Console
2. Get your WhatsApp-enabled phone number
3. Submit message templates for approval
4. Configure `TWILIO_WHATSAPP_FROM` with your business number

### 3. Register Blueprint

In your Flask application:

```python
from scrum_42_whatsapp_message_integration import whatsapp_bp

app.register_blueprint(whatsapp_bp)
```

## Usage Example

### Python

```python
import requests

response = requests.post(
    'http://localhost:5000/notifications/whatsapp',
    json={
        'task_id': 'task-123',
        'task_title': 'Complete project proposal',
        'recipient_number': '+15551234567'
    }
)

print(response.json())
```

### cURL

```bash
curl -X POST http://localhost:5000/notifications/whatsapp \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "task-123",
    "task_title": "Complete project proposal",
    "recipient_number": "+15551234567"
  }'
```

## Testing

Run the test suite:

```bash
pytest tests/
```

Run with coverage:

```bash
pytest tests/ --cov=. --cov-report=html
```

## Error Handling

The service implements comprehensive error handling:

1. **Validation Errors** (400): Missing required fields, invalid JSON
2. **Service Errors** (500): Twilio API errors, network issues
3. **Configuration Errors**: Missing environment variables

All errors are logged with detailed context for debugging.

## Message Format

Default message template:
```
Hey! Don't forget: {task_title} 🎯

{app_link}
```

Example:
```
Hey! Don't forget: Complete project proposal 🎯

https://flux-life-assistant.app/tasks/task-123
```

## Phone Number Format

Recipient numbers must be in E.164 format:
- ✅ `+15551234567` (with country code)
- ✅ `whatsapp:+15551234567` (with whatsapp: prefix - added automatically)
- ❌ `5551234567` (missing country code)
- ❌ `(555) 123-4567` (formatting not allowed)

## Architecture

```
scrum_42_whatsapp_message_integration/
├── __init__.py          # Module initialization
├── models.py            # Data models (WhatsAppNotification)
├── service.py           # WhatsApp service logic (Twilio integration)
├── routes.py            # REST API endpoints
├── requirements.txt     # Python dependencies
├── README.md            # Documentation
└── tests/               # Test suite
    ├── __init__.py
    ├── test_service.py
    └── test_routes.py
```

## Dependencies

- `twilio>=8.10.0` - Twilio SDK for WhatsApp messaging
- `flask>=3.0.0` - Web framework for REST API

## Acceptance Criteria

- ✅ WhatsApp message sent to configured sandbox/business number
- ✅ Message contains task title and app link
- ✅ If WhatsApp fails, error is logged and returned in response
- ✅ Support for both sandbox and production WhatsApp Business API

## Related Scrum Items

- SCRUM-40: Notification Priority Model
- SCRUM-41: Push Notification Integration
- SCRUM-43: Phone Call Trigger

## Support

For issues or questions, please refer to:
- [Twilio WhatsApp Documentation](https://www.twilio.com/docs/whatsapp)
- [Twilio Sandbox Setup](https://www.twilio.com/docs/whatsapp/sandbox)

## License

Part of Flux Life Assistant - AI-powered life management platform.

---

## Swagger / API Documentation

This module uses **Flask** with **flasgger**, which provides Swagger UI for interactive API documentation.

### Running the standalone API server

```bash
# From the backend/ directory
cd /workspaces/Flux-Team-8/backend
python3 scrum_42_whatsapp_message_integration/main.py
```

### Accessing Swagger UI

| Interface | URL |
|---|---|
| **Swagger UI** (interactive) | `http://localhost:8042/docs` |
| **OpenAPI JSON spec** | `http://localhost:8042/apispec.json` |

Once running, open `http://localhost:8042/docs` in your browser to explore and test all endpoints interactively.

### Installing dependencies

```bash
pip install flask flasgger
# or
pip install -r scrum_42_whatsapp_message_integration/requirements.txt
```
