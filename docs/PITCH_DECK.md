# Flux — Pitch Deck
> AI-Powered Goal & Task Management · Investor Presentation

---

## Slide 1 — The Problem

**Most people fail their goals not because they lack motivation — but because they lack a system.**

- 92% of people fail to achieve their New Year's goals _(University of Scranton)_
- The average person has 3–5 active productivity tools — and uses none of them consistently
- Existing apps are either too simple (reminders) or too complex (project management)
- **The missing piece:** a companion that turns vague intentions into structured, sustainable action — and follows through when you don't

---

## Slide 2 — The Solution

**Flux is a conversational AI companion that turns "I want to get fit" into a live, personalized plan — and holds you accountable through escalating notifications.**

- **Chat-first:** No forms, no dashboards to fill out. One conversation is all it takes to go from intention to a 6-week action plan.
- **Structured by science:** Goals are broken into ≤6-week sprints, designed to maintain a >70% completion rate (backed by behavioral research).
- **Follows through:** Push → WhatsApp → phone call escalation ensures you never silently skip a commitment.
- **Gets smarter:** The system learns your behavioral patterns and adjusts scheduling recommendations over time.

---

## Slide 3 — Product Walkthrough

### Step 1: Onboard in 2 minutes
A conversational setup collects your schedule, sleep window, work hours, and chronotype. No forms.

### Step 2: Tell Flux your goal
_"I want to run a 5K"_ → Flux asks 1–2 clarifying questions → proposes a 6-week plan with specific days, times, and durations → you confirm or negotiate.

### Step 3: Your plan is live
Tasks appear in your daily timeline. Inline "Done" and "Missed" actions. Tap to reschedule — Flux finds the next available slot. For recurring tasks, you choose: move just this session, or shift all future occurrences to the new time.

### Step 4: Flux follows up
10 minutes before a task: push notification.
No response? WhatsApp message.
Still no response? Phone call with DTMF options: Done · Reschedule · Missed.

### Step 5: Speak to Flux
Press and hold the mic button — Flux understands spoken goals, tasks, and rescheduling requests. Replies are read back aloud.

---

## Slide 4 — How It Works (Technical Architecture)

```
User speaks or types
        │
        ▼
   Chat Interface (TanStack Start / React SSR)
        │
        ▼
   FastAPI Backend
        │
        ▼
   LangGraph Agent Graph
   ┌─────────────────────────────────────────────┐
   │  Orchestrator → Goal Clarifier              │
   │       → Ask Start Date                      │
   │       → Goal Planner                        │
   │            ├── Classifier (parallel)        │
   │            ├── Scheduler (parallel)         │
   │            └── Pattern Observer (parallel)  │
   │       → Save Tasks                          │
   └─────────────────────────────────────────────┘
        │
        ▼
   Supabase (PostgreSQL + Auth + Realtime)
        │
        ▼
   Notifier Worker
   Push → WhatsApp (Twilio) → Voice Call (Twilio)
```

**Key architectural differentiators:**
- **Parallel agent fan-out** via LangGraph `Send()` — classifier, scheduler, and pattern observer run simultaneously, not sequentially.
- **Persistent multi-turn state** — a goal negotiation can span multiple sessions; the agent picks up exactly where it left off.
- **Voice as a transport layer** — Deepgram STT transcribes speech into the same pipeline as typed text. Zero agent changes required.

---

## Slide 5 — Voice Integration (Flagship Feature)

**Voice is the fastest path from intention to action.**

- **Push-to-talk** in the chat interface — speak your goal, task, or reschedule request.
- **Deepgram nova-3 STT** — low-latency streaming transcription, browser-native WebSocket.
- **Natural TTS response** — Flux reads back plan summaries and confirmations aloud (Deepgram aura-asteria-en).
- **Zero pipeline changes** — voice is a transport layer. The same LangGraph agents handle spoken and typed input identically.

> _"I want to start meditating in the mornings"_ — spoken in 3 seconds, 6-week plan generated and confirmed in under a minute.

**Why this matters for investors:**
Voice removes the last friction barrier. Users can interact with Flux while commuting, at the gym, or getting ready for work — without touching a screen.

---

## Slide 6 — Escalating Notification Engine

**The feature that separates Flux from every other reminder app.**

Most apps send one push notification and give up. Flux doesn't.

```
T - 10 min  →  Push notification (in-app CTA: Done · Reschedule · Missed)
  +2 min    →  WhatsApp message (if no response)
  +2 min    →  Phone call with voice menu (if no response)
  +2 min    →  Auto-marked missed; Pattern Observer notified
```

- **Per-task escalation policies:** Users can set tasks as `silent`, `standard`, or `aggressive` based on how important they are.
- **Twilio-powered:** WhatsApp Business API + Programmable Voice (TTS). Single vendor, proven infrastructure.
- **Behavioral learning:** After 3 consecutive misses in the same time slot, the Pattern Observer flags it and future plans avoid that slot.

---

## Slide 7 — Tech Stack

| Layer | Technology |
|---|---|
| Frontend | TanStack Start (React SSR + PWA) |
| Backend API | Python FastAPI |
| Agent Orchestration | LangGraph with AsyncPostgresSaver checkpointing |
| LLM Gateway | LiteLLM via OpenRouter (multi-provider, model-swappable) |
| Database | Supabase (PostgreSQL + Auth + Realtime) |
| Voice | Deepgram (STT nova-3 + TTS aura-asteria-en) |
| Notifications | Twilio (WhatsApp Business API + Programmable Voice) + Web Push |
| Monitoring | Sentry + LangSmith |

**LLM strategy — best model per agent:**
- Orchestrator: GPT-4o (intent classification + multi-turn reasoning)
- Goal Planner: Claude 3.5 Sonnet (long-context planning)
- All other agents: GPT-4o-mini (fast, cheap, structured output)

**Cost control:** Hard token budget per user — orchestrator automatically downgrades model on limit. Pattern Observer runs asynchronously (no blocking the chat response).

---

## Slide 8 — Behavioral Science Foundation

**Why 6 weeks? Why this structure?**

> _"Based on behavioral science research, humans maintain a >70% success rate when goals are structured as focused 6-week sprints."_

Flux's planning engine is built around three principles:

1. **Sustainability over ambition.** Week 1 of any plan is deliberately easy — building the habit before the load.
2. **Pattern avoidance.** The system learns which time slots you consistently skip and stops scheduling there.
3. **Micro-goal chains.** Goals too large for 6 weeks are decomposed into sequential milestones. Completing one automatically activates the next.

**Sleep-window enforcement** is applied deterministically at every scheduling layer — when tasks are first saved and when recurring tasks advance to their next occurrence. No reminder ever lands during the user's sleep window, regardless of when it was created or how frequently it recurs.

This isn't a reminder app. It's a behavioral change engine.

---

## Slide 9 — Roadmap

### Shipped in MVP
- ✅ Conversational onboarding
- ✅ Goal planning with 6-week sprints and pipeline micro-goals
- ✅ Standalone task creation and amendment
- ✅ Push → WhatsApp → Voice call escalation
- ✅ Voice input (STT) + spoken responses (TTS)
- ✅ Daily timeline view with inline task management
- ✅ Behavioral pattern tracking (Pattern Observer)
- ✅ Recurring tasks (RRULE) with projection
- ✅ Recurring series reschedule — move just one session or all future occurrences
- ✅ GDPR: data export + account deletion

### Phase 2
- React Native app (reuse FastAPI backend)
- Google Calendar bi-directional sync
- GPS geofencing (replace demo mode toggle)
- Pattern Observer UI (view, correct, dismiss learned patterns)
- Collaborative goals (accountability partners)
- Home screen widget (iOS/Android)

---

## Slide 10 — The Ask

_[To be defined by the team — funding amount, use of funds, timeline to Phase 2]_

**Contact:** _[Add contact details]_

---

_Flux — Turn intentions into habits._
