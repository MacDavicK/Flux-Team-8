# Phone Call Trigger API

**SCRUM-43: Phone Call Trigger**  
**Owner:** BE-B | **Points:** 3 | **Component:** `notifications`

## Overview

This module provides a Python-based FastAPI implementation for triggering phone calls with Text-to-Speech (TTS) messages and gathering user acknowledgments via DTMF (keypad) input. It integrates with Twilio's Voice API to enable critical task notifications through phone calls.

## Features

✅ **Twilio Voice API Integration**: Make automated phone calls  
✅ **Text-to-Speech (TTS)**: Play dynamic messages with task information  
✅ **DTMF Input Gathering**: Collect user acknowledgments via keypad press  
✅ **Webhook Handling**: Process call status and user input callbacks  
✅ **FastAPI Implementation**: Modern async Python API with automatic documentation  

## Requirements

### SCRUM-43 Acceptance Criteria

- [x] Call is placed to configured phone number
- [x] TTS message plays correctly with task title
- [x] Pressing 1 acknowledges the task via webhook

### Dependencies

- Python 3.9+
- FastAPI
- Twilio SDK (>=8.10.0)
- Pydantic
- Uvicorn

## Installation

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Environment Variables

Create a `.env` file in your backend root:

```env
# Twilio Configuration
TWILIO_ACCOUNT_SID=your_account_sid_here
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_PHONE_NUMBER=+1234567890  # Your Twilio phone number in E.164 format
```

**Get your Twilio credentials:**
1. Sign up at [twilio.com](https://www.twilio.com)
2. Navigate to Console Dashboard
3. Copy Account SID and Auth Token
4. Purchase or configure a phone number with Voice capabilities

### 3. Register Router in Main App

In your main FastAPI application file:

```python
from fastapi import FastAPI
from scrum_43_phone_call_trigger import router as phone_call_router

app = FastAPI()

# Include the phone call router
app.include_router(phone_call_router)
```

## API Endpoints

### 1. Initiate Phone Call

**POST** `/notifications/call`

Initiates a phone call with TTS message and gathers user acknowledgment.

**Request Body:**
```json
{
  "phone_number": "+14155551234",
  "task_title": "Submit quarterly report",
  "task_id": "task_12345"  // optional
}
```

**Response (201):**
```json
{
  "call_sid": "CA1234567890abcdef",
  "status": "queued",
  "to": "+14155551234",
  "message": "Call initiated successfully to +14155551234",
  "initiated_at": "2026-02-15T08:00:00Z"
}
```

### 2. TwiML Generation (Webhook)

**POST** `/notifications/call/twiml`

Internal webhook endpoint called by Twilio. Generates TwiML XML response.

### 3. Handle Gather Input (Webhook)

**POST** `/notifications/call/gather`

Processes DTMF digits pressed by user during the call.

### 4. Call Status Updates (Webhook)

**POST** `/notifications/call/status`

Receives call status updates from Twilio (completed, failed, etc.)

## Call Flow

```
1. POST /notifications/call
   ↓
2. Twilio initiates call to user's phone
   ↓
3. Twilio requests TwiML from /notifications/call/twiml
   ↓
4. TTS message plays: "Hi! This is Flux. You have a critical task: {task_title}. Press 1 to acknowledge."
   ↓
5. User presses 1 (or times out)
   ↓
6. Twilio sends digit to /notifications/call/gather
   ↓
7. If digit == "1": "Thank you. Task acknowledged. Goodbye."
   Else: "No acknowledgment received. Goodbye."
   ↓
8. Call ends
   ↓
9. Status callback sent to /notifications/call/status
```

## Testing

### Using cURL

```bash
curl -X POST http://localhost:8000/notifications/call \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "+14155551234",
    "task_title": "Submit quarterly report",
    "task_id": "task_12345"
  }'
```

### Using FastAPI's Interactive Docs

1. Start your FastAPI server
2. Navigate to `http://localhost:8000/docs`
3. Find the `/notifications/call` endpoint
4. Click "Try it out" and enter request data
5. Execute the request

## Module Structure

```
scrum_43_phone_call_trigger/
├── __init__.py          # Module initialization and exports
├── models.py            # Pydantic data models
├── service.py           # Twilio service integration
├── routes.py            # FastAPI route handlers
├── requirements.txt     # Python dependencies
└── README.md            # This file
```

## Architecture

### Components

1. **Models** (`models.py`): Pydantic models for request/response validation
   - `CallRequest`: Input for initiating calls
   - `CallResponse`: Call initiation response
   - `GatherResponse`: DTMF input processing

2. **Service** (`service.py`): Twilio API integration
   - `TwilioCallService`: Handles Twilio SDK operations
   - Call initiation
   - Status retrieval

3. **Routes** (`routes.py`): FastAPI endpoints
   - `POST /notifications/call`: Initiate call
   - `POST /notifications/call/twiml`: Generate TwiML
   - `POST /notifications/call/gather`: Process user input
   - `POST /notifications/call/status`: Handle status callbacks

## Integration with Task Management

The TODO comment in `routes.py` indicates where to integrate with your task management system:

```python
# TODO: Integrate with task management system to mark task as acknowledged
# This would typically involve calling another service or updating a database
```

Example integration:
```python
if acknowledged:
    # Call your task service
    await task_service.mark_acknowledged(task_id)
    # Or publish an event
    await event_bus.publish(TaskAcknowledgedEvent(task_id))
```

## Security Considerations

1. **Twilio Request Validation**: Consider implementing request signature validation for webhooks
2. **Environment Variables**: Never commit `.env` files with real credentials
3. **Phone Number Validation**: The API validates E.164 format
4. **Rate Limiting**: Consider implementing rate limits for the initiate call endpoint

## Error Handling

- **503**: Twilio service not initialized (check environment variables)
- **500**: Twilio API errors (check credentials and phone number configuration)
- **422**: Invalid request body (phone number format, missing fields)

## Logging

The module uses Python's standard `logging` module. Configure logging in your main application:

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

## References

- [Twilio Voice API Documentation](https://www.twilio.com/docs/voice)
- [TwiML Voice Documentation](https://www.twilio.com/docs/voice/twiml)
- [Twilio Gather Documentation](https://www.twilio.com/docs/voice/twiml/gather)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

---

**Built for SCRUM-43 | Flux Life Assistant**
