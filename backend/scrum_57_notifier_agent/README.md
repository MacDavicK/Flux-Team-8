# Notifier Agent (SCRUM-57)

The **Notifier Agent** is a background service responsible for monitoring task states and driving the Flux multi-channel escalation ladder.

## Overview

The agent consists of two main components running in a single process:
1.  **FastAPI Web Server:** Serves webhook endpoints for Twilio (WhatsApp/Voice) and in-app task actions.
2.  **APScheduler Loop:** Polls the database (via `dao_service`) every 60 seconds to identify tasks requiring escalation.

## Escalation Logic

| Time | Action | Condition |
| :--- | :--- | :--- |
| `T - 10m` | **Push Notification** | Task is `SCHEDULED`. |
| `T + 2m` | **WhatsApp Message** | Push sent but task still `SCHEDULED`. |
| `T + 4m` | **Phone Call** | WhatsApp sent but task still `SCHEDULED`. |
| `T + 6m` | **Auto-Miss** | Call initiated but task still `SCHEDULED`. |

*Note: `T` is the `scheduled_at` time of the task.*

## Webhook Endpoints

- `POST /api/webhooks/twilio/whatsapp`: Handles user replies (1/2/3).
- `POST /api/webhooks/twilio/voice`: Serves TwiML and handles DTMF digits.
- `POST /api/demo/location-trigger`: MVP endpoint for "I'm away from home" demo.

## Setup

1.  Create a `.env` file from `.env.example`.
2.  Install dependencies: `pip install -r requirements.txt`.
3.  Start the service: `python main.py`.

## Architecture Notes

- **Separation of Concerns:** The agent does **not** access the database directly. It uses the `DaoTaskService` for all persistence.
- **State Management:** Notification progress (e.g., `whatsapp_sent_at`) is tracked in-memory and synced to the database.
