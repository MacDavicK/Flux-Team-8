# Notifications (Priority, Push, Call)

> Last verified: 2026-03-01

## What it does

Multi-channel escalation: **push** → **WhatsApp** → **call** by priority (standard, important, must-not-miss). Implemented by SCRUM modules (40: priority model, 41: push, 42: WhatsApp, 43: phone call, 44: escalation demo). This is not a single agent; it is a set of services that a **notifier** process or cron job typically calls when a task is due or missed. The orchestrator usually does not call these directly.

## How to run

When SCRUM routers are loaded, they are mounted on the **main** Flux app. Start the main backend:

```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload
```

If some SCRUM modules fail to import, the main app still runs but without those routes. Standalone apps (e.g. SCRUM 44, 57) are documented in their own READMEs in `backend/`.

## Connection

HTTP. Base paths below assume the main app base URL (e.g. `http://localhost:8000`). All are optional depending on which SCRUM modules are installed.

| Module | Base path | Key endpoints | Routes file |
|--------|-----------|---------------|-------------|
| **Priority / config** | `/api/v1/notifications/priority` | POST `/send`, GET `/config`, GET `/timing`, GET `/health` | [notification_priority_model/routes.py](../../backend/notification_priority_model/routes.py) |
| **Push** | `/notifications/push` | POST `` (send), POST `/subscribe`, DELETE `/unsubscribe`, GET `/vapid-public-key` | [push_notification_integration/routes.py](../../backend/push_notification_integration/routes.py) |
| **Call** | `/notifications/call` | POST `` (trigger), POST `/twiml`, POST `/gather`, POST `/status` | [phone_call_trigger/routes.py](../../backend/phone_call_trigger/routes.py) |

WhatsApp (SCRUM 42) and Escalation Demo (SCRUM 44) may use different stacks (e.g. Flask Blueprint); see their READMEs in `backend/whatsapp_message_integration/` and `backend/escalation_demo_ui/`.

## When the orchestrator uses it

The orchestrator typically does **not** call notification endpoints directly. A separate **notifier** (or scheduled job) does:

1. Determine that a task is due or missed (e.g. from DAO or main app task state).
2. Call the priority API to get escalation path and timing (e.g. POST `/api/v1/notifications/priority/send` with priority and speed multiplier).
3. The priority service (or notifier) then triggers push, then WhatsApp, then call according to the escalation rules.

If you are building an orchestrator that must trigger a notification (e.g. “send reminder for task X”), you can either call the priority send endpoint with `task_id`/metadata or integrate with a notifier API (e.g. SCRUM 57 Notifier Agent) that then calls these endpoints. See each SCRUM README for request bodies and webhooks.

## Links

- **SCRUM 40** — [backend/notification_priority_model/README.md](../../backend/notification_priority_model/README.md)
- **SCRUM 41** — [backend/push_notification_integration/README.md](../../backend/push_notification_integration/README.md)
- **SCRUM 42** — [backend/whatsapp_message_integration/README.md](../../backend/whatsapp_message_integration/README.md)
- **SCRUM 43** — [backend/phone_call_trigger/README.md](../../backend/phone_call_trigger/README.md)
- **SCRUM 44** — [backend/escalation_demo_ui/README.md](../../backend/escalation_demo_ui/README.md)
- **SCRUM 57 (Notifier Agent)** — [backend/notifier_agent/](../../backend/notifier_agent/) (if present)
- If the repo has a high-level **notification escalation** doc (e.g. `docs/notification-escalation.md`), link it here for a one-page summary of push → WhatsApp → call flow.
