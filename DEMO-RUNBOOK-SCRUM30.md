# SCRUM-30 Scheduler Agent — Demo Runbook

> **Duration:** ~8 minutes  
> **Format:** Live screen share  
> **Audience:** Teammates (they can clone and run locally after)  

---

## Pre-Demo Setup (do this 10 min before the call)

### 1. Seed the database

```bash
# Option A: Local Supabase (Docker) — run after bash scripts/supabase_setup.sh
# Setup script seeds seed_test_data.sql; then add scheduler demo:
docker cp supabase/scripts/seed_scheduler_demo.sql supabase_db_Flux-Team-8:/tmp/seed_scheduler_demo.sql
docker exec supabase_db_Flux-Team-8 psql -U postgres -f /tmp/seed_scheduler_demo.sql

# Option B: psql (if installed and DATABASE_URL set)
psql $DATABASE_URL -f supabase/scripts/seed_test_data.sql
psql $DATABASE_URL -f supabase/scripts/seed_scheduler_demo.sql

# Option C: Paste into Supabase Dashboard → SQL Editor
# Copy contents of both files and run them in order
```

**Verify the seed worked** — run this query in the SQL Editor:
```sql
SELECT id, title, state,
       to_char(start_time, 'HH24:MI') AS start_hh,
       to_char(end_time, 'HH24:MI')   AS end_hh
FROM tasks
WHERE user_id = 'a1000000-0000-0000-0000-000000000001'
ORDER BY start_time;
```

You should see "Gym Session" with state = `drifted`, plus "Lunch Break" and "Spanish Lesson" as `scheduled`.

### 2. Start the backend

```bash
cd ~/Downloads/Flux/backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

Hit `http://localhost:8000/health` — should return `{"status": "ok"}`.

### 3. Start the frontend

```bash
cd ~/Downloads/Flux/frontend
npm run dev
```

Opens at `http://localhost:3000` (or 3001 if 3000 is busy).

### 4. Open these tabs before the call
- **Tab 1:** Terminal with backend running
- **Tab 2:** Terminal ready for curl commands
- **Tab 3:** Browser at `http://localhost:3000`
- **Tab 4:** Supabase Dashboard → Table Editor → `tasks` table (filtered to Alice)

---

## Demo Script

### Act 1: Backend API (2-3 min)

> **What to say:** "Let me start by showing what the scheduler does at the API level. We have a task called 'Gym Session' that was scheduled for 7 AM this morning but drifted — the user didn't complete it. Let's ask the scheduler for suggestions."

**1a. Call the suggest endpoint:**
```bash
curl -s -X POST http://localhost:8000/scheduler/suggest \
  -H "Content-Type: application/json" \
  -d '{"event_id": "d2000000-0000-0000-0000-000000000001"}' | python3 -m json.tool
```

> **What to say:** "The agent scans today and tomorrow in 30-minute slots, skips sleep hours and existing tasks — Lunch Break at noon, Spanish at 7 PM — and returns the best options with a rationale. Notice it avoids work hours and includes a 15-minute buffer."

**Expected output shape:**
```json
{
  "event_id": "d2000000-...",
  "task_title": "Gym Session",
  "suggestions": [
    {
      "new_start": "2026-03-01T18:00:00+00:00",
      "new_end": "2026-03-01T19:00:00+00:00",
      "label": "6:00 PM Today",
      "rationale": "Suggested 6:00 PM — it's your next free slot outside work hours today."
    },
    {
      "new_start": "2026-03-02T07:00:00+00:00",
      "new_end": "2026-03-02T08:00:00+00:00",
      "label": "7:00 AM Sunday",
      "rationale": "Suggested 7:00 AM Sunday — same time as originally planned."
    }
  ],
  "skip_option": true,
  "ai_message": "Gym Session drifted. I can do:"
}
```

> **What to say:** "The agent scored each slot. The tomorrow-7-AM slot scores highest because it matches the original time (+20 points) AND it's outside work hours (+10). Today's slot only gets the work-hours bonus. But we show both so the user has a choice."

**1b. Apply a reschedule:**
```bash
curl -s -X POST http://localhost:8000/scheduler/apply \
  -H "Content-Type: application/json" \
  -d '{
    "event_id": "d2000000-0000-0000-0000-000000000001",
    "action": "reschedule",
    "new_start": "2026-03-01T18:00:00+00:00",
    "new_end": "2026-03-01T19:00:00+00:00"
  }' | python3 -m json.tool
```

> **What to say:** "Task is now rescheduled. Let me show you in Supabase."

**Switch to Tab 4 (Supabase Dashboard)** — refresh the tasks table. Show that "Gym Session" state changed from `drifted` → `scheduled` and the times updated.

**1c. Reset for Act 2** — run this to put the task back to drifted:
```sql
UPDATE tasks
SET state = 'drifted',
    start_time = (CURRENT_DATE + INTERVAL '7 hours')::timestamptz,
    end_time   = (CURRENT_DATE + INTERVAL '8 hours')::timestamptz
WHERE id = 'd2000000-0000-0000-0000-000000000001';
```

---

### Act 2: Frontend UI (3-4 min)

> **What to say:** "Now let me show the user experience. The frontend runs in mock mode for this demo — same UI, same flow, just with canned data so we don't need auth wired up yet."

**2a. Show the timeline:**

Open browser at `http://localhost:3000`. Point out:
- The "Gym Session" card has a **terracotta glow** and a **pulsing dot** — that's how drifted tasks look
- There's a **"Shuffle?" button** on the drifted card

> **What to say:** "Any task that enters the 'drifted' state gets this visual treatment. The pulsing dot draws attention, and the Shuffle button opens the negotiation flow."

**2b. Tap "Shuffle?":**

Click the "Shuffle?" button. The **NegotiationModal** opens. Walk through:
1. **Loading state** — skeleton shimmer (flashes briefly)
2. **AI message** — "Gym drifted. I can do:"
3. **Suggestion buttons** — each shows a label (e.g., "5:00 PM Today") and a rationale underneath
4. **Skip Today** — at the bottom

> **What to say:** "The modal fetches suggestions from the scheduler agent. Each option has a rationale explaining why the agent picked that slot. The user just taps one."

**2c. Pick an option:**

Tap one of the suggestion buttons. Show:
- The modal closes
- The task card **animates** to its new time slot on the timeline
- The drifted visual treatment (glow + pulsing dot) is gone

> **What to say:** "One tap. The task moves, the timeline updates. No forms, no date pickers."

**2d. Demo Skip Today:**

If time permits, reset and show "Skip Today":
- Task card disappears from the timeline
- The next recurrence stays on the schedule

---

### Act 3: Voice Negotiation — Stretch (1-2 min)

> **Only demo this if the team is interested AND you're in Chrome.**

**Requirements:** Chrome browser, microphone permission granted.

> **What to say:** "We also have a voice layer. When the modal opens, it speaks the AI message and listens for a response."

1. Open the modal (tap "Shuffle?" again)
2. You'll hear TTS: "Gym drifted. I can do..."
3. The "Listening..." indicator appears with a pulsing mic
4. Say **"Yes"** — maps to the first suggestion, auto-applies
5. Or say **"Skip"** — marks as missed

> **What to say:** "This is the SCRUM-34 stretch goal. Voice is opt-in and falls back to the tap UI if the browser doesn't support Web Speech API."

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `curl` returns 400 "not drifted" | Re-run the reset SQL from step 1c |
| Backend won't start (import error) | `source .venv/bin/activate` — make sure you're in the venv |
| Frontend shows blank | Check `npm run dev` output for port; try `http://localhost:3001` |
| No voice in modal | Must be Chrome; check mic permissions in browser settings |
| Suggestions show wrong times | The seed uses UTC; your local display may offset. Mention this. |

---

## Talking Points for Q&A

- **"Why template rationale instead of LLM?"** — MVP ships with deterministic templates (instant, free, no API call). There's a config flag `scheduler_use_llm_rationale` — flipping it to `true` activates GPT-4o-mini for natural language rationale with zero code changes.

- **"How does slot scoring work?"** — Two signals: +10 for outside work hours, +20 for matching the original scheduled time. Pattern Observer integration (v2) will add completion-rate weighting.

- **"What about recurring tasks?"** — Skip Today marks the single occurrence as missed. The `is_recurring` flag is preserved so the next occurrence stays on schedule. Full RRULE expansion is Phase 2.

- **"How does the frontend know a task is drifted?"** — The `state` field on the task object. `TimelineEvent` checks `isDrifted` prop → applies terracotta glow + pulsing dot + "Shuffle?" button.

---

## After the Demo

Share with the team:
```
# Clone and run locally:
git clone https://github.com/MacDavicK/Flux-Team-8.git
cd Flux-Team-8
git checkout backend          # for BE code
git checkout feature/scheduler-fe  # for FE code

# Seed + run:
psql $DATABASE_URL -f supabase/scripts/seed_test_data.sql
psql $DATABASE_URL -f supabase/scripts/seed_scheduler_demo.sql
cd backend && source .venv/bin/activate && uvicorn app.main:app --reload
cd frontend && npm install && npm run dev
```
