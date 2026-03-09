# Notification Escalation

Flux uses a **multi-channel escalation** path: **Push → WhatsApp → Phone call**, based on task priority and acknowledgment.

---

## Priority levels

| Priority | Channels | Wait times (typical) |
|---------|----------|------------------------|
| **Standard** | Push only | No escalation |
| **Important** | Push → WhatsApp | WhatsApp after ~2 min if no acknowledgment |
| **Must-Not-Miss** | Push → WhatsApp → Call | WhatsApp after ~2 min; call after ~7 min total if no acknowledgment |

---

## Escalation speed multiplier

Demo and testing support a speed multiplier (e.g. 1x, 5x, 10x):

- **1x:** Normal wait times (2 min, 7 min).
- **5x:** 5× faster (e.g. 2 min → 24 s).
- **10x:** 10× faster (e.g. 2 min → 12 s).

Controlled via the Escalation Demo UI or backend escalation APIs.

---

## Implementation modules (SCRUM 40–44)

Each channel and the priority model is implemented in a separate backend module with its own API and README:

| SCRUM | Module | Description |
|-------|--------|-------------|
| **40** | [scrum_40_notification_priority_model](../backend/scrum_40_notification_priority_model/README.md) | Priority model and escalation path (send with priority, get escalation steps) |
| **41** | [scrum_41_push_notification_integration](../backend/scrum_41_push_notification_integration/README.md) | Web Push (VAPID, subscription, send push) |
| **42** | [scrum_42_whatsapp_message_integration](../backend/scrum_42_whatsapp_message_integration/README.md) | WhatsApp via Twilio (templated task reminders) |
| **43** | [scrum_43_phone_call_trigger](../backend/scrum_43_phone_call_trigger/README.md) | Twilio Voice (TTS, DTMF acknowledgment) |
| **44** | [scrum_44_escalation_demo_ui](../backend/scrum_44_escalation_demo_ui/README.md) | Escalation demo API (multi-channel with speed control) |

These modules are **not** mounted on the main Flux FastAPI app (`app.main:app`). They are standalone or mountable separately; see each README for endpoints and setup.

---

## Summary

1. **Priority** (SCRUM-40) decides the path (push-only vs push→WhatsApp→call).
2. **Push** (SCRUM-41) sends the first notification.
3. If no ack, **WhatsApp** (SCRUM-42) sends the next step.
4. For must-not-miss, **Call** (SCRUM-43) is the final step.
5. **Demo UI** (SCRUM-44) drives the full escalation with configurable speed for demos.
